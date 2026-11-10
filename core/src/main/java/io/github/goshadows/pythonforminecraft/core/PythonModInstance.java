/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CopyOnWriteArrayList;

import org.graalvm.polyglot.PolyglotException;
import org.graalvm.polyglot.Value;

/**
 * One loaded Python mod: its descriptor, its own Python runtime and its Java-side state.
 *
 * <p>Life cycle: {@link #bootstrap()} (unpack sources, install the bridge, import the
 * declared modules), {@link #runPhase(PyFm.Phase)} for each declared entry point, then
 * {@link #dispatch(String, Object)} per event and {@link #shutdown()} on stop.</p>
 */
public final class PythonModInstance {

    private final PythonModDescriptor descriptor;
    private final PythonRuntime runtime;
    private final JavaBridge bridge;
    private final Path pythonDir;
    private final List<String> vendorPaths;
    private final List<CommandSpec> commands = new CopyOnWriteArrayList<>();
    private final List<PyFm.Phase> completedPhases = new CopyOnWriteArrayList<>();
    private volatile boolean bootstrapped;
    private volatile boolean shutDown;
    private volatile boolean failed;
    private volatile String failureReport;

    public PythonModInstance(final PythonModDescriptor descriptor, final PythonRuntime runtime,
                             final Path pythonDir, final List<String> vendorPaths) {
        this.descriptor = Objects.requireNonNull(descriptor, "descriptor");
        this.runtime = Objects.requireNonNull(runtime, "runtime");
        this.pythonDir = pythonDir;
        this.vendorPaths = vendorPaths == null ? List.of() : List.copyOf(vendorPaths);
        this.bridge = new JavaBridge(this);
    }

    public PythonModDescriptor descriptor() {
        return this.descriptor;
    }

    public PythonRuntime runtime() {
        return this.runtime;
    }

    public Path pythonDir() {
        return this.pythonDir;
    }

    public boolean isBootstrapped() {
        return this.bootstrapped;
    }

    public boolean isShutDown() {
        return this.shutDown;
    }

    /** True when Python code of this mod failed; such a mod is never reported as loaded. */
    public boolean failed() {
        return this.failed;
    }

    /** The formatted failure report, or {@code null}. */
    public String failureReport() {
        return this.failureReport;
    }

    public List<PyFm.Phase> completedPhases() {
        return List.copyOf(this.completedPhases);
    }

    public List<CommandSpec> commands() {
        return List.copyOf(this.commands);
    }

    /** Installs the bridge, bootstraps the Python runtime and imports declared modules. */
    public void bootstrap() {
        if (this.bootstrapped) {
            return;
        }
        if (this.shutDown) {
            throw new PyFmException("this Python mod has already been shut down",
                    this.descriptor.modId(), "bootstrap");
        }
        try {
            this.runtime.call("_install_bridge", this.bridge);
            this.runtime.call("_bootstrap", this.descriptor.modId(),
                    this.descriptor.side().id(), bootstrapConfig());
            this.bootstrapped = true;
            PyFm.log().info("{} Python mod '{}' ({}) bootstrapped on the {} side; sources at {}",
                    PyFm.LOG_PREFIX, this.descriptor.modId(), this.descriptor.version(),
                    this.descriptor.side().id(), this.pythonDir);
        } catch (final PolyglotException exception) {
            this.failed = true;
            this.failureReport = PythonTracebacks.format(exception,
                    this.descriptor.modId(), "bootstrap", this.runtime);
            throw PythonTracebacks.toException(exception, this.descriptor.modId(),
                    "bootstrap", this.runtime);
        }
    }

    /**
     * Runs *phase* for the entry point declared for it.
     *
     * <p>A phase that does not belong to this mod's side is skipped. A Python failure is
     * rethrown as {@link PyFmException} so the loader reports the mod as failed.</p>
     */
    public void runPhase(final PyFm.Phase phase) {
        runPhase(phase, this.descriptor.entrypoint(phase));
    }

    /**
     * Runs *phase* against an explicitly declared entry point.
     *
     * <p>Fabric hands the entry point string to the language adapter without exposing the
     * whole metadata, so the Fabric adapter passes the spec itself.</p>
     */
    public void runPhase(final PyFm.Phase phase, final String spec) {
        if (!phase.runsOn(this.descriptor.side())) {
            PyFm.log().debug("{} skipping phase {} of '{}' (side {})", PyFm.LOG_PREFIX,
                    phase.id(), this.descriptor.modId(), this.descriptor.side().id());
            return;
        }
        if (spec == null) {
            return;
        }
        bootstrap();
        try {
            final Value ran = this.runtime.call("_load_entrypoint", spec, phase.id(),
                    this.descriptor.modId());
            this.completedPhases.add(phase);
            PyFm.log().info("{} entry point {} of '{}' ran for {}: {}", PyFm.LOG_PREFIX, spec,
                    this.descriptor.modId(), phase.id(),
                    ran != null && !ran.isNull() ? ran.toString() : "[]");
        } catch (final PolyglotException exception) {
            this.failed = true;
            this.failureReport = PythonTracebacks.format(exception,
                    this.descriptor.modId(), phase.id() + " (" + spec + ")", this.runtime);
            throw PythonTracebacks.toException(exception, this.descriptor.modId(),
                    phase.id() + " (" + spec + ")", this.runtime);
        }
    }

    /** Dispatches one event to this mod and returns the Python-side summary line. */
    public String dispatch(final String event, final Object payload) {
        if (this.shutDown || !this.bootstrapped) {
            return "event=" + event + " mod=" + this.descriptor.modId() + " skipped";
        }
        final Thread affinity = this.runtime.affinity();
        if (affinity != null && affinity != Thread.currentThread()) {
            PyFm.log().warn("{} event {} for '{}' arrives on thread '{}' but the mod was "
                            + "initialised on '{}'", PyFm.LOG_PREFIX, event,
                    this.descriptor.modId(), Thread.currentThread().getName(),
                    affinity.getName());
        }
        try {
            final Value summary = this.runtime.call("_dispatch", event, payload,
                    this.descriptor.modId());
            return summary == null || summary.isNull() ? "event=" + event : summary.asString();
        } catch (final PolyglotException exception) {
            final String report = PythonTracebacks.format(exception, this.descriptor.modId(),
                    "event " + event, this.runtime);
            PyFm.log().error("{}", report);
            return "event=" + event + " mod=" + this.descriptor.modId() + " errors=1";
        }
    }

    /** Runs a command callback registered by this mod. */
    public int invokeCommand(final String key, final Object source, final List<String> args) {
        if (this.shutDown) {
            return 0;
        }
        try {
            final Value result = this.runtime.call("_invoke_command", key, source,
                    args == null ? List.<String>of() : args);
            return result == null || result.isNull() ? 0 : result.asInt();
        } catch (final PolyglotException exception) {
            PyFm.log().error("{}", PythonTracebacks.format(exception,
                    this.descriptor.modId(), "command " + key, this.runtime));
            return 0;
        }
    }

    /** Called from the bridge when Python registers a command. */
    void addCommand(final CommandSpec spec) {
        this.commands.add(spec);
    }

    /** Called from the bridge by {@code pfm} when Python reports a fatal error. */
    void markFailed(final String message) {
        this.failed = true;
        if (this.failureReport == null) {
            this.failureReport = message;
        }
    }

    /** Releases handlers, commands and entry points, then closes the Python runtime. */
    public void shutdown() {
        if (this.shutDown) {
            return;
        }
        this.shutDown = true;
        if (this.bootstrapped) {
            try {
                this.runtime.call("_shutdown", this.descriptor.modId());
            } catch (final RuntimeException exception) {
                PyFm.log().warn("{} failed to shut down the Python runtime of '{}': {}",
                        PyFm.LOG_PREFIX, this.descriptor.modId(), exception.toString());
            }
        }
        this.runtime.close();
        this.commands.clear();
        PyFm.log().info("{} Python mod '{}' released", PyFm.LOG_PREFIX,
                this.descriptor.modId());
    }

    private java.util.List<String> runtimePaths() {
        final Path runtimeDir = PyFmLifecycle.runtimePythonDir();
        return runtimeDir == null ? java.util.List.of()
                : java.util.List.of(runtimeDir.toAbsolutePath().toString());
    }

    private String bootstrapConfig() {
        final Map<String, String> metadata = new LinkedHashMap<>();
        metadata.put("mod_id", Json.quote(this.descriptor.modId()));
        metadata.put("version", Json.quote(this.descriptor.version()));
        metadata.put("display_name", Json.quote(this.descriptor.displayName()));
        metadata.put("side", Json.quote(this.descriptor.side().id()));
        metadata.put("python_root", Json.quote(this.descriptor.pythonRoot()));
        final Map<String, String> config = new LinkedHashMap<>();
        config.put("metadata", Json.object(metadata));
        config.put("runtime_paths", Json.array(runtimePaths()));
        config.put("vendor_paths", Json.array(this.vendorPaths));
        config.put("modules", Json.array(this.descriptor.modules()));
        return Json.object(config);
    }
}

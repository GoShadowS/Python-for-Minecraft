/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

import org.graalvm.polyglot.Engine;
import org.graalvm.polyglot.Value;

/**
 * Every Python mod loaded in this JVM, plus the engine they share.
 */
public final class PythonModRegistry {

    private static final Map<String, PythonModInstance> INSTANCES = new ConcurrentHashMap<>();
    private static volatile Engine engine;

    private PythonModRegistry() {
    }

    /** The shared engine, created on first use. */
    public static synchronized Engine engine() {
        if (engine == null) {
            engine = PythonRuntime.newEngine();
            PyFm.log().info("{} GraalPy engine started (GraalPy {})", PyFm.LOG_PREFIX,
                    PyFm.GRAALPY_VERSION);
        }
        return engine;
    }

    /** Registers a mod instance, rejecting a duplicate mod id. */
    public static void register(final PythonModInstance instance) {
        final String modId = instance.descriptor().modId();
        final PythonModInstance previous = INSTANCES.putIfAbsent(modId, instance);
        if (previous != null) {
            throw new PyFmException("a Python mod with id '" + modId
                    + "' is already loaded", modId, "registration");
        }
    }

    public static Optional<PythonModInstance> get(final String modId) {
        return Optional.ofNullable(INSTANCES.get(modId));
    }

    public static boolean isRegistered(final String modId) {
        return INSTANCES.containsKey(modId);
    }

    public static Collection<PythonModInstance> all() {
        return INSTANCES.values();
    }

    /** Diagnostics snapshot produced by the Python side of every loaded mod. */
    public static String statusJson() {
        final List<String> parts = new ArrayList<>();
        for (final PythonModInstance instance : INSTANCES.values()) {
            if (!instance.isBootstrapped() || instance.isShutDown()) {
                continue;
            }
            try {
                final Value status = instance.runtime().call("_status_json");
                if (status != null && !status.isNull()) {
                    parts.add(status.asString());
                }
            } catch (final RuntimeException exception) {
                PyFm.log().debug("{} could not read the status of '{}': {}",
                        PyFm.LOG_PREFIX, instance.descriptor().modId(), exception.toString());
            }
        }
        return "[" + String.join(",", parts) + "]";
    }

    /** Shuts every Python mod down and closes the shared engine. */
    public static synchronized void shutdownAll() {
        for (final PythonModInstance instance : INSTANCES.values()) {
            try {
                instance.shutdown();
            } catch (final RuntimeException exception) {
                PyFm.log().warn("{} failed to shut down '{}': {}", PyFm.LOG_PREFIX,
                        instance.descriptor().modId(), exception.toString());
            }
        }
        INSTANCES.clear();
        Commands.clear();
        Handles.clear();
        if (engine != null) {
            try {
                engine.close(true);
            } catch (final RuntimeException exception) {
                PyFm.log().warn("{} failed to close the Python engine: {}", PyFm.LOG_PREFIX,
                        exception.toString());
            }
            engine = null;
        }
        PyFm.log().info("{} Python runtime released", PyFm.LOG_PREFIX);
    }
}

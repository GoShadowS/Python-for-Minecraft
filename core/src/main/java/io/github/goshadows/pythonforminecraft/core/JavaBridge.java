/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.Locale;
import java.util.Objects;

/**
 * The object Python code sees as the bridge (see {@code pfm/_bridge.py} for the contract).
 *
 * <p>Only primitives and plain objects cross the boundary, so the bridge does not depend on
 * Truffle converting Python collections into Java ones. Method names use underscores
 * because that is how Python calls them.</p>
 */
public final class JavaBridge {

    private final PythonModInstance instance;

    public JavaBridge(final PythonModInstance instance) {
        this.instance = Objects.requireNonNull(instance, "instance");
    }

    /** The mod this bridge belongs to. */
    public String mod_id() {
        return this.instance.descriptor().modId();
    }

    /** {@code "client"} or {@code "server"}. */
    public String side() {
        return this.instance.descriptor().side().id();
    }

    /** Writes a Python log line into the game log, prefixed with the mod id. */
    public void log(final String level, final String message) {
        final String text = "{} '{}' {}";
        final Object[] args = {PyFm.LOG_PREFIX, mod_id(), message};
        switch (level == null ? "info" : level.toLowerCase(Locale.ROOT)) {
            case "debug" -> PyFm.log().debug(text, args);
            case "warn", "warning" -> PyFm.log().warn(text, args);
            case "error" -> PyFm.log().error(text, args);
            default -> PyFm.log().info(text, args);
        }
    }

    /** Called by {@code pfm.command()}; every argument is a primitive. */
    public void register_command(final String name, final String key, final String usage,
                                 final int permission, final String side) {
        final CommandSpec spec = new CommandSpec(mod_id(), name, key, usage, permission,
                side == null || side.isBlank() || "both".equalsIgnoreCase(side)
                        ? this.instance.descriptor().side() : PyFm.Side.of(side));
        this.instance.addCommand(spec);
        Commands.register(spec, this.instance);
    }

    /** Sends a reply to a command source, through the loader's own API. */
    public void reply(final Object source, final String text) {
        Commands.reply(source, text);
    }

    /**
     * Resolves a Java class.
     *
     * <p>Inside GraalPy, {@code pfm.java.import_class} prefers GraalPy's own
     * {@code java.type()}, which returns a class symbol with working static members; this
     * method is the fallback and returns the {@link Class} object.</p>
     */
    public Object import_class(final String name) {
        try {
            return Class.forName(name, false, getClass().getClassLoader());
        } catch (final ClassNotFoundException exception) {
            throw new PyFmException("no such Java class: " + name, mod_id(), "java interop",
                    exception);
        }
    }

    /** A well known game handle ({@code server}, {@code client}, {@code player}) or null. */
    public Object get_handle(final String name) {
        return Handles.get(name);
    }

    /** Lets Python report a fatal problem; recorded on the instance and logged. */
    public void fail(final String message) {
        this.instance.markFailed(message);
        PyFm.log().error("{} Python mod '{}' reported a fatal error: {}", PyFm.LOG_PREFIX,
                mod_id(), message);
    }
}

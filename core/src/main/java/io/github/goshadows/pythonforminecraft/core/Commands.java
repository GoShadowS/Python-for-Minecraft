/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Bridge between commands registered in Python and the loader's command API.
 */
public final class Commands {

    private static final Map<String, PythonModInstance> OWNERS = new ConcurrentHashMap<>();
    private static final Map<String, CommandSpec> SPECS = new ConcurrentHashMap<>();
    private static volatile CommandRegistrar registrar;
    private static volatile CommandReplier replier;

    private Commands() {
    }

    /** Called once by the loader adapter that owns command registration. */
    public static void setRegistrar(final CommandRegistrar value) {
        registrar = value;
    }

    public static CommandRegistrar registrar() {
        return registrar;
    }

    /** Installs the loader-specific "send a message to a command source" implementation. */
    public static void setReplier(final CommandReplier value) {
        replier = value;
    }

    /** Sends *text* to *source*; silently ignored when no replier is installed. */
    public static void reply(final Object source, final String text) {
        final CommandReplier current = replier;
        if (current == null) {
            PyFm.log().warn("{} no command replier is installed; dropping reply: {}",
                    PyFm.LOG_PREFIX, text);
            return;
        }
        current.reply(source, text);
    }

    /**
     * Registers a command declared by Python.
     *
     * <p>Without a registrar the command is remembered but not wired up, and a warning is
     * logged: that is the situation when neither the client nor the server-capable
     * component of Python-for-Minecraft is installed.</p>
     */
    public static void register(final CommandSpec spec, final PythonModInstance owner) {
        OWNERS.put(spec.key(), owner);
        SPECS.put(spec.key(), spec);
        final CommandRegistrar current = registrar;
        if (current == null) {
            PyFm.log().warn("{} command /{} of Python mod '{}' is registered but no loader "
                    + "command registrar is present; install the client or the server-capable "
                    + "component of Python-for-Minecraft", PyFm.LOG_PREFIX, spec.name(),
                    spec.modId());
            return;
        }
        current.register(spec);
        PyFm.log().info("{} registered /{} for Python mod '{}' via {}", PyFm.LOG_PREFIX,
                spec.name(), spec.modId(), current.loader());
    }

    /**
     * Runs the Python callback of the command identified by *key*.
     *
     * @return {@code true} when a Python callback handled it
     */
    public static boolean dispatch(final String key, final Object source,
                                   final List<String> args) {
        final PythonModInstance owner = OWNERS.get(key);
        if (owner == null) {
            return false;
        }
        return owner.invokeCommand(key, source, args) > 0;
    }

    public static Collection<String> keys() {
        return OWNERS.keySet();
    }

    /** Every command registered so far; loader registrars iterate this when they build. */
    public static Collection<CommandSpec> specs() {
        return SPECS.values();
    }

    public static void clear() {
        OWNERS.clear();
        SPECS.clear();
    }

    /** Sends text back to a command source using the loader's own API. */
    public interface CommandReplier {
        void reply(Object source, String text);
    }
}

/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

/**
 * The events Python mods can subscribe to, and the dispatcher loader adapters call.
 *
 * <p>Names are identical on both loaders; the payload is whatever the adapter passes, and
 * Python receives it as {@code event.data}.</p>
 */
public final class PythonEvents {

    /** After the common entry point ran, on both sides. */
    public static final String INITIALIZE = "initialize";
    /** Client startup finished. */
    public static final String CLIENT_START = "client_start";
    /** Client is stopping. */
    public static final String CLIENT_STOP = "client_stop";
    /** Dedicated or integrated server is starting. */
    public static final String SERVER_START = "server_start";
    /** Server is stopping. */
    public static final String SERVER_STOP = "server_stop";
    /** One client tick, on the client thread. */
    public static final String CLIENT_TICK = "client_tick";
    /** One server tick, on the server thread. */
    public static final String SERVER_TICK = "server_tick";
    /** A player joined; payload is the player. */
    public static final String PLAYER_JOIN = "player_join";
    /** A player left; payload is the player. */
    public static final String PLAYER_LEAVE = "player_leave";

    private PythonEvents() {
    }

    /**
     * Dispatches *event* with *payload* to every loaded Python mod.
     *
     * <p>Side filtering happens in Python: a handler declared for the client is skipped in a
     * server-side runtime. One mod failing never stops the others.</p>
     */
    public static void dispatch(final String event, final Object payload) {
        for (final PythonModInstance instance : PythonModRegistry.all()) {
            final String summary = instance.dispatch(event, payload);
            if (PyFm.log().isDebugEnabled()) {
                PyFm.log().debug("{} {}", PyFm.LOG_PREFIX, summary);
            } else if (summary != null && summary.contains("errors=")
                    && !summary.endsWith("errors=0")) {
                PyFm.log().error("{} {}", PyFm.LOG_PREFIX, summary);
            }
        }
    }
}

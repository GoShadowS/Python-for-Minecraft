/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.fabric;

import io.github.goshadows.pythonforminecraft.core.Handles;
import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import io.github.goshadows.pythonforminecraft.core.PythonEvents;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;

/**
 * Client component of Python-for-Minecraft on Fabric.
 *
 * <p>Lives in a jar with {@code "environment": "client"}, so a dedicated server never loads
 * this class. It starts the runtime, wires client events to Python and stops the runtime
 * when the client closes.</p>
 */
public final class PyFmClient implements ClientModInitializer {

    @Override
    public void onInitializeClient() {
        PyFmLifecycle.start(FabricLoader.getInstance().getGameDir(), PyFm.Side.CLIENT);
        FabricCommands.install();
        registerEvents();
        PyFm.log().info("{} client component ready (Python mods run on the client only "
                + "unless the server-capable component is installed)", PyFm.LOG_PREFIX);
    }

    private static void registerEvents() {
        ClientLifecycleEvents.CLIENT_STARTED.register(client -> {
            Handles.put(Handles.CLIENT, client);
            PythonEvents.dispatch(PythonEvents.CLIENT_START, client);
        });
        ClientLifecycleEvents.CLIENT_STOPPING.register(client -> {
            PythonEvents.dispatch(PythonEvents.CLIENT_STOP, client);
            Handles.remove(Handles.CLIENT);
            PyFmLifecycle.stop();
        });
        ClientTickEvents.START_CLIENT_TICK.register(
                client -> PythonEvents.dispatch(PythonEvents.CLIENT_TICK, client));
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) ->
                PythonEvents.dispatch(PythonEvents.PLAYER_JOIN, handler.localPlayer));
        ClientPlayConnectionEvents.DISCONNECT.register((handler, client) ->
                PythonEvents.dispatch(PythonEvents.PLAYER_LEAVE, handler.localPlayer));
    }
}

/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.fabric;

import io.github.goshadows.pythonforminecraft.core.Handles;
import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import io.github.goshadows.pythonforminecraft.core.PythonEvents;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;

/**
 * Server-capable component of Python-for-Minecraft on Fabric.
 *
 * <p>Its jar has {@code "environment": "*"}, so the {@code main} entry point runs both on a
 * dedicated server and on a client. On a client it only wires server events, which is what
 * makes Python server logic work in single player (the integrated server); the runtime
 * itself is started by whichever component runs first.</p>
 */
public final class PyFmServer implements ModInitializer {

    @Override
    public void onInitialize() {
        PyFmLifecycle.start(FabricLoader.getInstance().getGameDir(),
                FabricPythonMods.currentSide());
        FabricCommands.install();
        registerEvents();
        PyFm.log().info("{} server-capable component ready on the {} side", PyFm.LOG_PREFIX,
                FabricPythonMods.currentSide().id());
    }

    private static void registerEvents() {
        ServerLifecycleEvents.SERVER_STARTING.register(server -> {
            Handles.put(Handles.SERVER, server);
            PythonEvents.dispatch(PythonEvents.SERVER_START, server);
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
            PythonEvents.dispatch(PythonEvents.SERVER_STOP, server);
            Handles.remove(Handles.SERVER);
            if (FabricPythonMods.currentSide() == PyFm.Side.SERVER) {
                PyFmLifecycle.stop();
            }
        });
        ServerTickEvents.START_SERVER_TICK.register(
                server -> PythonEvents.dispatch(PythonEvents.SERVER_TICK, server));
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
                PythonEvents.dispatch(PythonEvents.PLAYER_JOIN, handler.getPlayer()));
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) ->
                PythonEvents.dispatch(PythonEvents.PLAYER_LEAVE, handler.getPlayer()));
    }
}

/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import io.github.goshadows.pythonforminecraft.core.Handles;
import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import io.github.goshadows.pythonforminecraft.core.PythonEvents;
import net.neoforged.event.tick.ServerTickEvent;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.server.ServerStartingEvent;
import net.neoforged.neoforge.event.server.ServerStoppedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;

/**
 * Server-capable component of Python-for-Minecraft on NeoForge.
 *
 * <p>This jar is a normal mod ({@code modLoader = "javafml"}); the Python mod loader itself
 * lives in the library jar with {@code FMLModType: LIBRARY}. Install this jar on a dedicated
 * server for Python server code, or on a client to get server events for the integrated
 * server.</p>
 */
@Mod(PyFm.SERVER_MOD_ID)
public final class PyFmNeoForgeServer {

    public PyFmNeoForgeServer() {
        PyFmLifecycle.start(FMLPaths.GAMEDIR.get(), NeoForgePythonMods.currentSide());
        NeoForgeCommands.install();
        NeoForge.EVENT_BUS.addListener(this::onServerStarting);
        NeoForge.EVENT_BUS.addListener(this::onServerTick);
        NeoForge.EVENT_BUS.addListener(this::onServerStopping);
        NeoForge.EVENT_BUS.addListener(this::onServerStopped);
        NeoForge.EVENT_BUS.addListener(this::onPlayerJoined);
        NeoForge.EVENT_BUS.addListener(this::onPlayerLeft);
        PyFm.log().info("{} server-capable component ready on the {} side", PyFm.LOG_PREFIX,
                NeoForgePythonMods.currentSide().id());
    }

    private void onServerStarting(final ServerStartingEvent event) {
        Handles.put(Handles.SERVER, event.getServer());
        PythonEvents.dispatch(PythonEvents.SERVER_START, event.getServer());
    }

    private void onServerTick(final ServerTickEvent.Pre event) {
        PythonEvents.dispatch(PythonEvents.SERVER_TICK, event.getServer());
    }

    private void onServerStopping(final ServerStoppingEvent event) {
        PythonEvents.dispatch(PythonEvents.SERVER_STOP, event.getServer());
    }

    private void onServerStopped(final ServerStoppedEvent event) {
        Handles.remove(Handles.SERVER);
        if (NeoForgePythonMods.currentSide() == PyFm.Side.SERVER) {
            PyFmLifecycle.stop();
        }
    }

    private void onPlayerJoined(final PlayerEvent.PlayerLoggedInEvent event) {
        PythonEvents.dispatch(PythonEvents.PLAYER_JOIN, event.getEntity());
    }

    private void onPlayerLeft(final PlayerEvent.PlayerLoggedOutEvent event) {
        PythonEvents.dispatch(PythonEvents.PLAYER_LEAVE, event.getEntity());
    }
}

/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import io.github.goshadows.pythonforminecraft.core.Handles;
import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import io.github.goshadows.pythonforminecraft.core.PythonEvents;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.GameShuttingDownEvent;

/**
 * Client-only event wiring.
 *
 * <p>This class touches client classes and must only be loaded on a client; it is referenced
 * from {@link PyFmNeoForgeClient} inside a {@code Dist.CLIENT} check.</p>
 */
final class ClientHooks {

    private ClientHooks() {
    }

    static void register() {
        NeoForge.EVENT_BUS.addListener(ClientHooks::onClientTick);
        NeoForge.EVENT_BUS.addListener(ClientHooks::onPlayerJoined);
        NeoForge.EVENT_BUS.addListener(ClientHooks::onPlayerLeft);
        NeoForge.EVENT_BUS.addListener(ClientHooks::onGameShuttingDown);
        Handles.put(Handles.CLIENT, net.minecraft.client.Minecraft.getInstance());
        PythonEvents.dispatch(PythonEvents.CLIENT_START,
                net.minecraft.client.Minecraft.getInstance());
    }

    private static void onClientTick(final ClientTickEvent.Pre event) {
        PythonEvents.dispatch(PythonEvents.CLIENT_TICK,
                net.minecraft.client.Minecraft.getInstance());
    }

    private static void onPlayerJoined(final ClientPlayerNetworkEvent.LoggingIn event) {
        PythonEvents.dispatch(PythonEvents.PLAYER_JOIN, event.getPlayer());
    }

    private static void onPlayerLeft(final ClientPlayerNetworkEvent.LoggingOut event) {
        PythonEvents.dispatch(PythonEvents.PLAYER_LEAVE, event.getPlayer());
    }

    private static void onGameShuttingDown(final GameShuttingDownEvent event) {
        PythonEvents.dispatch(PythonEvents.CLIENT_STOP,
                net.minecraft.client.Minecraft.getInstance());
        Handles.remove(Handles.CLIENT);
        PyFmLifecycle.stop();
    }
}

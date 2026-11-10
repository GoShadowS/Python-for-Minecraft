/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.fml.loading.FMLPaths;

/**
 * Client component of Python-for-Minecraft on NeoForge.
 *
 * <p>NeoForge has no per-mod-file side flag, so this class may be loaded anywhere; every
 * client API is reached only through {@link ClientHooks}, which is referenced inside a
 * {@link Dist#CLIENT} check and therefore never loaded on a dedicated server.</p>
 */
@Mod(PyFm.CLIENT_MOD_ID)
public final class PyFmNeoForgeClient {

    public PyFmNeoForgeClient() {
        PyFmLifecycle.start(FMLPaths.GAMEDIR.get(), NeoForgePythonMods.currentSide());
        NeoForgeCommands.install();
        if (FMLEnvironment.getDist() == Dist.CLIENT) {
            ClientHooks.register();
            PyFm.log().info("{} client component ready (Python mods run on the client only "
                    + "unless the server-capable component is installed)", PyFm.LOG_PREFIX);
        } else {
            PyFm.log().warn("{} the client component is installed on a dedicated server; it "
                    + "stays inactive and no client class is loaded. Remove it from the "
                    + "server to save memory.", PyFm.LOG_PREFIX);
        }
    }
}

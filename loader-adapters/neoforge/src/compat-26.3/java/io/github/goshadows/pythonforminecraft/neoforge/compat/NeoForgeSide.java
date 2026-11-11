/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge.compat;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.loading.FMLEnvironment;

/**
 * Which side this JVM runs, for NeoForge 26.x / Minecraft 26.3.
 *
 * <p>Counterpart of the 21.1 variant: this FancyModLoader line exposes the side as
 * {@code public static Dist getDist()}, not as the {@code public static final Dist dist}
 * field of FML 4.x. Verified against FancyModLoader main,
 * {@code loader/src/main/java/net/neoforged/fml/loading/FMLEnvironment.java}.</p>
 */
public final class NeoForgeSide {

    private NeoForgeSide() {
    }

    /** @return the side FML detected for this JVM. */
    public static Dist current() {
        return FMLEnvironment.getDist();
    }
}

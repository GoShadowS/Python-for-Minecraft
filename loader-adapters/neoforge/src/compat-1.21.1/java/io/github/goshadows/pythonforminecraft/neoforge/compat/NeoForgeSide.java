/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge.compat;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.loading.FMLEnvironment;

/**
 * Which side this JVM runs, for NeoForge 21.x / Minecraft 1.21.1.
 *
 * <p>This class is deliberately duplicated per target. FancyModLoader@1.21.1 declares
 * {@code public static final Dist dist = FMLLoader.getDist();} -- a field -- while the
 * FancyModLoader line that ships with NeoForge 26.3 replaced it with
 * {@code public static Dist getDist()}. Neither spelling compiles against the other, and
 * {@code FMLLoader.getDist()} is not a portable substitute either: it is static in FML 4.x
 * and an instance method in FML 12.x. Everything else in the adapter is shared; only this
 * lookup is not.</p>
 */
public final class NeoForgeSide {

    private NeoForgeSide() {
    }

    /** @return the side FML detected for this JVM. */
    public static Dist current() {
        return FMLEnvironment.dist;
    }
}

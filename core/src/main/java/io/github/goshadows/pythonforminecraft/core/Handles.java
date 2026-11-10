/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Well known game handles exposed to Python as {@code pfm.mc.<name>}.
 *
 * <p>Loader adapters put the current {@code MinecraftServer} under {@code "server"} and the
 * {@code Minecraft} client under {@code "client"}; the values are cleared again when those
 * objects stop existing, so Python never holds on to a dead server.</p>
 */
public final class Handles {

    public static final String SERVER = "server";
    public static final String CLIENT = "client";
    public static final String PLAYER = "player";

    private static final Map<String, Object> VALUES = new ConcurrentHashMap<>();

    private Handles() {
    }

    public static void put(final String name, final Object value) {
        if (value == null) {
            VALUES.remove(name);
        } else {
            VALUES.put(name, value);
        }
    }

    /** The handle, or {@code null}; never throws for an unknown name. */
    public static Object get(final String name) {
        return name == null ? null : VALUES.get(name);
    }

    public static void remove(final String name) {
        VALUES.remove(name);
    }

    public static void clear() {
        VALUES.clear();
    }
}

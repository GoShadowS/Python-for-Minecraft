/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.Objects;

/**
 * A command a Python mod registered with {@code @pfm.command}.
 *
 * @param modId      owning Python mod
 * @param name       command name without a leading slash
 * @param key        {@code "<modId>:<name>"}, what the loader calls back with
 * @param usage      usage string shown in help
 * @param permission vanilla-style permission level, 0 for everyone
 * @param side       side the command is available on
 */
public record CommandSpec(String modId, String name, String key, String usage,
                          int permission, PyFm.Side side) {

    public CommandSpec {
        Objects.requireNonNull(modId, "modId");
        Objects.requireNonNull(name, "name");
        if (name.isBlank() || name.contains(" ") || name.startsWith("/")) {
            throw new PyFmException(
                    "command name must be a single word without a leading slash: '" + name
                            + "'", modId, "command registration");
        }
        if (key == null || key.isBlank()) {
            key = modId + ":" + name;
        }
        if (usage == null || usage.isBlank()) {
            usage = "/" + name;
        }
        if (side == null) {
            side = PyFm.Side.SERVER;
        }
    }
}

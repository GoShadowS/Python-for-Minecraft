/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

/**
 * Implemented by the loader adapters: turns a {@link CommandSpec} into a real command of
 * the loader's command API (Brigadier on both Fabric and NeoForge).
 *
 * <p>Keeping this behind an interface is what lets Python code register {@code /pyhello}
 * without knowing which loader it runs on.</p>
 */
public interface CommandRegistrar {

    /** Registers one command. Must be safe to call from the Python thread. */
    void register(CommandSpec spec);

    /** Loader name for log lines, e.g. {@code "fabric"} or {@code "neoforge"}. */
    String loader();
}

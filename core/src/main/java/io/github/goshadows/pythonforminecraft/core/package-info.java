/**
 * Loader-agnostic core of Python-for-Minecraft.
 *
 * <p>This package must never reference Minecraft, Fabric or NeoForge types: the core
 * artifact is loaded on both sides, and a dedicated server must not be able to reach a
 * client class through it.</p>
 *
 * <p>The Python side of the same contract lives in {@code python/pfm}; the calls that cross
 * the boundary are documented in {@code JavaBridge} and in {@code pfm/__init__.py}.</p>
 */
package io.github.goshadows.pythonforminecraft.core;

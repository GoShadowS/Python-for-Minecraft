/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Validation of the {@code "package.module:attribute"} entry point notation.
 *
 * <p>Java validates the shape and hands the string to Python, which does the actual import
 * and resolution. Keeping one notation for both loaders is deliberate: a Python mod author
 * writes the same string in {@code fabric.mod.json} and in {@code neoforge.mods.toml}.</p>
 */
public final class PythonEntrypoints {

    private static final Pattern SPEC = Pattern.compile(
            "^([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*):([A-Za-z_][A-Za-z0-9_]*)$");

    private PythonEntrypoints() {
    }

    /**
     * @throws PyFmException when *spec* is not {@code package.module:attribute}
     */
    public static void validate(final String spec, final String modId) {
        if (spec == null || spec.isBlank()) {
            throw new PyFmException("entry point must not be empty", modId, "metadata");
        }
        if (!SPEC.matcher(spec.trim()).matches()) {
            throw new PyFmException(
                    "invalid entry point '" + spec + "', expected 'package.module:attribute'",
                    modId, "metadata");
        }
    }

    /** The module part of *spec*; validated first. */
    public static String moduleOf(final String spec, final String modId) {
        validate(spec, modId);
        final Matcher matcher = SPEC.matcher(spec.trim());
        return matcher.matches() ? matcher.group(1) : spec;
    }

    /** The attribute part of *spec*; validated first. */
    public static String attributeOf(final String spec, final String modId) {
        validate(spec, modId);
        final Matcher matcher = SPEC.matcher(spec.trim());
        return matcher.matches() ? matcher.group(2) : spec;
    }
}

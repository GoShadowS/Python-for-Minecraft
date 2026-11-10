/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

/**
 * Thrown when a Python mod cannot be loaded or when Python code fails.
 *
 * <p>Carries the mod id and the phase so that loader adapters can turn it into a
 * loader-native failure ({@code LanguageAdapterException} on Fabric,
 * {@code ModLoadingException} on NeoForge) instead of reporting a broken mod as loaded.</p>
 */
public class PyFmException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String modId;
    private final String phase;

    public PyFmException(final String message) {
        this(message, null, null, null);
    }

    public PyFmException(final String message, final Throwable cause) {
        this(message, null, null, cause);
    }

    public PyFmException(final String message, final String modId, final String phase) {
        this(message, modId, phase, null);
    }

    public PyFmException(final String message, final String modId, final String phase,
                         final Throwable cause) {
        super(describe(message, modId, phase), cause);
        this.modId = modId;
        this.phase = phase;
    }

    private static String describe(final String message, final String modId,
                                   final String phase) {
        final StringBuilder builder = new StringBuilder(PyFm.LOG_PREFIX);
        if (modId != null) {
            builder.append(" Python mod '").append(modId).append('\'');
        }
        if (phase != null) {
            builder.append(" during ").append(phase);
        }
        return builder.append(": ").append(message).toString();
    }

    /** The mod that failed, when known. */
    public String modId() {
        return this.modId;
    }

    /** The phase that failed, when known. */
    public String phase() {
        return this.phase;
    }
}

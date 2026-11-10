/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import java.util.Properties;

/**
 * Configuration of the Python runtime, read from
 * {@code <game directory>/config/pythonforminecraft.properties}.
 *
 * <p>Every key has a safe default, so the file is optional. Recognised keys:</p>
 * <pre>
 * python.allowAllAccess=true    # host access given to Python code, see docs/security.md
 * python.workDir=pythonforminecraft
 * python.debug=false
 * </pre>
 */
public final class PyFmConfig {

    public static final String FILE_NAME = "pythonforminecraft.properties";

    private final boolean allowAllAccess;
    private final String workDirName;
    private final boolean debug;

    private PyFmConfig(final boolean allowAllAccess, final String workDirName,
                       final boolean debug) {
        this.allowAllAccess = allowAllAccess;
        this.workDirName = workDirName;
        this.debug = debug;
    }

    /** Defaults: trusted Python code, work directory {@code pythonforminecraft}. */
    public static PyFmConfig defaults() {
        return new PyFmConfig(true, "pythonforminecraft", false);
    }

    /**
     * Loads the configuration from {@code configDir/pythonforminecraft.properties}.
     * A missing or unreadable file yields {@link #defaults()}.
     */
    public static PyFmConfig load(final Path configDir) {
        final PyFmConfig fallback = defaults();
        if (configDir == null) {
            return fallback;
        }
        final Path file = configDir.resolve(FILE_NAME);
        if (!Files.isRegularFile(file)) {
            return fallback;
        }
        final Properties properties = new Properties();
        try (InputStream in = Files.newInputStream(file)) {
            properties.load(in);
        } catch (final IOException exception) {
            PyFm.log().warn("{} could not read {}: {}", PyFm.LOG_PREFIX, file,
                    exception.toString());
            return fallback;
        }
        return new PyFmConfig(
                bool(properties, "python.allowAllAccess", fallback.allowAllAccess),
                properties.getProperty("python.workDir", fallback.workDirName),
                bool(properties, "python.debug", fallback.debug));
    }

    private static boolean bool(final Properties properties, final String key,
                                final boolean fallback) {
        final String raw = properties.getProperty(key);
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        final String value = raw.trim().toLowerCase(Locale.ROOT);
        if (value.equals("true") || value.equals("1") || value.equals("yes")) {
            return true;
        }
        if (value.equals("false") || value.equals("0") || value.equals("no")) {
            return false;
        }
        PyFm.log().warn("{} ignoring invalid boolean for {}: {}", PyFm.LOG_PREFIX, key, raw);
        return fallback;
    }

    /**
     * Whether Python code gets unrestricted host access.
     *
     * <p>Python mods are <em>not</em> sandboxed: with this enabled (the default) Python code
     * has the same reach as the game process itself. See {@code docs/security.md}.</p>
     */
    public boolean allowAllAccess() {
        return this.allowAllAccess;
    }

    /** Directory, relative to the game directory, where Python sources are unpacked. */
    public String workDirName() {
        return this.workDirName;
    }

    /** Extra diagnostics: per-event dispatch summaries at info level. */
    public boolean debug() {
        return this.debug;
    }
}

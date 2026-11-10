/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Start/stop of the Python runtime inside one JVM.
 *
 * <p>The client adapter starts it on the client, the server-capable adapter starts it on a
 * dedicated server; both call {@link #stop()} when the game stops. A JVM shutdown hook is
 * installed as a safety net so contexts are released even on a hard exit path.</p>
 */
public final class PyFmLifecycle {

    private static Path gameDir;
    private static Path runtimePythonDir;
    private static PyFmConfig config;
    private static PyFm.Side side;
    private static boolean started;
    private static Thread shutdownHook;

    private PyFmLifecycle() {
    }

    /** Starts the runtime. Calling it twice is a no-op. */
    public static synchronized void start(final Path gameDirectory, final PyFm.Side currentSide) {
        if (started) {
            return;
        }
        gameDir = gameDirectory;
        side = currentSide;
        config = PyFmConfig.load(gameDirectory == null ? null : gameDirectory.resolve("config"));
        try {
            Files.createDirectories(workDir());
            runtimePythonDir = PyFmRuntimeResources.ensure(workDir());
        } catch (final IOException exception) {
            throw new PyFmException("cannot create the Python work directory " + workDir()
                    + ": " + exception, null, "startup", exception);
        }
        started = true;
        installShutdownHook();
        PyFm.log().info("{} Python-for-Minecraft {} starting on the {} side (work dir {})",
                PyFm.LOG_PREFIX, PyFm.VERSION, currentSide.id(), workDir());
    }

    public static synchronized boolean isStarted() {
        return started;
    }

    public static Path gameDir() {
        return gameDir;
    }

    public static PyFm.Side side() {
        return side;
    }

    public static PyFmConfig config() {
        return config == null ? PyFmConfig.defaults() : config;
    }

    /** Directory holding the unpacked {@code pfm} package; goes first on sys.path. */
    public static Path runtimePythonDir() {
        return runtimePythonDir;
    }

    /** Where Python sources and vendored packages are unpacked. */
    public static Path workDir() {
        final Path base = gameDir == null ? Path.of(".") : gameDir;
        return base.resolve(config().workDirName());
    }

    /** Releases every Python mod, the engine and the shutdown hook. */
    public static synchronized void stop() {
        if (!started) {
            return;
        }
        PythonModRegistry.shutdownAll();
        started = false;
        if (shutdownHook != null) {
            try {
                Runtime.getRuntime().removeShutdownHook(shutdownHook);
            } catch (final IllegalStateException ignored) {
                // The JVM is already shutting down; the hook itself does the work.
            }
            shutdownHook = null;
        }
        PyFm.log().info("{} Python-for-Minecraft stopped", PyFm.LOG_PREFIX);
    }

    private static void installShutdownHook() {
        if (shutdownHook != null) {
            return;
        }
        shutdownHook = new Thread(() -> {
            try {
                PythonModRegistry.shutdownAll();
            } catch (final RuntimeException exception) {
                // Nothing sensible left to do while the JVM is dying.
            }
        }, "PythonForMinecraft-Shutdown");
        Runtime.getRuntime().addShutdownHook(shutdownHook);
    }
}

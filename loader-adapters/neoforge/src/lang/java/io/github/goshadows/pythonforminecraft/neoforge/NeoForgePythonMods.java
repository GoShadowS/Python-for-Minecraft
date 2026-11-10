/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmException;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import io.github.goshadows.pythonforminecraft.core.PyFmLogStream;
import io.github.goshadows.pythonforminecraft.core.PythonModDescriptor;
import io.github.goshadows.pythonforminecraft.core.PythonModFiles;
import io.github.goshadows.pythonforminecraft.core.PythonModInstance;
import io.github.goshadows.pythonforminecraft.core.PythonModRegistry;
import io.github.goshadows.pythonforminecraft.core.PythonRuntime;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforgespi.language.IModFileInfo;
import net.neoforged.neoforgespi.language.IModInfo;

/**
 * Reads {@code neoforge.mods.toml} into a {@link PythonModDescriptor} and creates the
 * runtime of a Python mod.
 *
 * <p>NeoForge has no entry point key, so a Python mod declares its entry points in
 * {@code [modproperties.<modId>]} as {@code pyfm_main}, {@code pyfm_client} and
 * {@code pyfm_server}; FML exposes that table through
 * {@link IModInfo#getModProperties()}.</p>
 */
public final class NeoForgePythonMods {

    /** Property key of the directory holding the Python sources. */
    public static final String KEY_PYTHON_ROOT = "python_root";
    /** Property key of the vendored dependency directories. */
    public static final String KEY_VENDOR = "vendor";
    /** Property key of the packages to import at bootstrap. */
    public static final String KEY_MODULES = "modules";
    /** Property key of the common entry point. */
    public static final String KEY_MAIN = "pyfm_main";
    /** Property key of the client entry point. */
    public static final String KEY_CLIENT = "pyfm_client";
    /** Property key of the dedicated-server entry point. */
    public static final String KEY_SERVER = "pyfm_server";

    private NeoForgePythonMods() {
    }

    /** The side this JVM runs. */
    public static PyFm.Side currentSide() {
        return FMLEnvironment.getDist() == Dist.CLIENT ? PyFm.Side.CLIENT : PyFm.Side.SERVER;
    }

    /** Parses the mod properties of *info*. */
    public static PythonModDescriptor describe(final IModInfo info) {
        final Map<String, Object> properties = info.getModProperties();
        final PythonModDescriptor.Builder builder =
                PythonModDescriptor.builder(info.getModId(), currentSide())
                        .displayName(info.getDisplayName())
                        .version(info.getVersion().toString())
                        .source(sourceOf(info));
        builder.pythonRoot(text(properties, KEY_PYTHON_ROOT, "python"));
        for (final String value : list(properties, KEY_VENDOR)) {
            builder.addVendorDir(value);
        }
        final List<String> modules = list(properties, KEY_MODULES);
        if (modules.isEmpty()) {
            builder.addModule(info.getModId());
        } else {
            for (final String module : modules) {
                builder.addModule(module);
            }
        }
        builder.entrypoint(PyFm.Phase.INITIALIZE, text(properties, KEY_MAIN, null));
        builder.entrypoint(PyFm.Phase.CLIENT_INITIALIZE, text(properties, KEY_CLIENT, null));
        builder.entrypoint(PyFm.Phase.SERVER_INITIALIZE, text(properties, KEY_SERVER, null));
        return builder.build();
    }

    /** Creates and bootstraps the runtime of *descriptor*. */
    public static PythonModInstance create(final PythonModDescriptor descriptor) {
        final String modId = descriptor.modId();
        if (!PyFmLifecycle.isStarted()) {
            PyFmLifecycle.start(FMLPaths.GAMEDIR.get(), currentSide());
        }
        final Path pythonDir;
        try {
            pythonDir = PythonModFiles.pythonPath(descriptor, PyFmLifecycle.workDir());
        } catch (final IOException exception) {
            throw new PyFmException("cannot unpack the Python sources: " + exception, modId,
                    "unpack", exception);
        }
        final PythonRuntime runtime = PythonRuntime.create(PythonModRegistry.engine(), modId,
                PyFmLifecycle.config(), new PyFmLogStream(modId, false),
                new PyFmLogStream(modId, true));
        final PythonModInstance instance = new PythonModInstance(descriptor, runtime, pythonDir,
                PythonModFiles.vendorPaths(descriptor, pythonDir));
        PythonModRegistry.register(instance);
        return instance;
    }

    private static Path sourceOf(final IModInfo info) {
        try {
            final IModFileInfo fileInfo = info.getOwningFile();
            return fileInfo == null ? null : fileInfo.getFile().getFilePath();
        } catch (final RuntimeException exception) {
            PyFm.log().warn("{} cannot determine the jar of Python mod '{}': {}",
                    PyFm.LOG_PREFIX, info.getModId(), exception.toString());
            return null;
        }
    }

    private static String text(final Map<String, Object> properties, final String key,
                               final String fallback) {
        final Object value = properties == null ? null : properties.get(key);
        if (value == null) {
            return fallback;
        }
        final String text = value.toString().trim();
        return text.isEmpty() ? fallback : text;
    }

    private static List<String> list(final Map<String, Object> properties, final String key) {
        final Object value = properties == null ? null : properties.get(key);
        if (value instanceof List<?> items) {
            return items.stream().map(Object::toString).map(String::trim)
                    .filter(item -> !item.isEmpty()).toList();
        }
        if (value instanceof String text && !text.isBlank()) {
            return List.of(text.trim());
        }
        return List.of();
    }
}

/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.fabric;

import java.nio.file.Path;
import java.util.List;
import java.util.Optional;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmLifecycle;
import io.github.goshadows.pythonforminecraft.core.PyFmLogStream;
import io.github.goshadows.pythonforminecraft.core.PyFmException;
import io.github.goshadows.pythonforminecraft.core.PythonModDescriptor;
import io.github.goshadows.pythonforminecraft.core.PythonModFiles;
import io.github.goshadows.pythonforminecraft.core.PythonModInstance;
import io.github.goshadows.pythonforminecraft.core.PythonModRegistry;
import io.github.goshadows.pythonforminecraft.core.PythonRuntime;
import net.fabricmc.api.EnvType;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;
import net.fabricmc.loader.api.metadata.CustomValue;
import net.fabricmc.loader.api.metadata.ModMetadata;
import net.fabricmc.loader.api.metadata.ModOrigin;

/**
 * Turns a Fabric mod into a {@link PythonModInstance}.
 *
 * <p>The Python-specific settings of a Fabric mod live in
 * {@code custom.pythonforminecraft} of its {@code fabric.mod.json}; the entry point itself
 * is the {@code value} of an entry point declared with {@code "adapter": "python"}.</p>
 */
public final class FabricPythonMods {

    /** Key of the {@code custom} block in fabric.mod.json. */
    public static final String CUSTOM_KEY = "pythonforminecraft";

    private FabricPythonMods() {
    }

    /** Returns the existing instance for *mod*, creating and bootstrapping it if needed. */
    public static PythonModInstance getOrCreate(final ModContainer mod) {
        final String modId = mod.getMetadata().getId();
        final Optional<PythonModInstance> existing = PythonModRegistry.get(modId);
        if (existing.isPresent()) {
            return existing.get();
        }
        final PythonModDescriptor descriptor = describe(mod);
        if (!PyFmLifecycle.isStarted()) {
            PyFmLifecycle.start(FabricLoader.getInstance().getGameDir(), currentSide());
        }
        final Path pythonDir;
        try {
            pythonDir = PythonModFiles.pythonPath(descriptor, PyFmLifecycle.workDir());
        } catch (final java.io.IOException exception) {
            throw new PyFmException("cannot unpack the Python sources: " + exception, modId,
                    "unpack", exception);
        }
        final PythonRuntime runtime = PythonRuntime.create(PythonModRegistry.engine(), modId,
                PyFmLifecycle.config(), new PyFmLogStream(modId, false),
                new PyFmLogStream(modId, true));
        final PythonModInstance instance = new PythonModInstance(descriptor, runtime, pythonDir,
                PythonModFiles.vendorPaths(descriptor, pythonDir));
        PythonModRegistry.register(instance);
        instance.bootstrap();
        return instance;
    }

    /** Reads the mod metadata into a loader-neutral descriptor. */
    public static PythonModDescriptor describe(final ModContainer mod) {
        final ModMetadata metadata = mod.getMetadata();
        final PythonModDescriptor.Builder builder =
                PythonModDescriptor.builder(metadata.getId(), currentSide())
                        .displayName(metadata.getName())
                        .version(metadata.getVersion().getFriendlyString())
                        .source(sourceOf(mod));
        final CustomValue custom = metadata.containsCustomValue(CUSTOM_KEY)
                ? metadata.getCustomValue(CUSTOM_KEY) : null;
        if (custom == null) {
            builder.pythonRoot("python");
            builder.addModule(metadata.getId());
            return builder.build();
        }
        final CustomValue.CvObject object = custom.getAsObject();
        builder.pythonRoot(string(object, "python_root", "python"));
        for (final String value : strings(object, "vendor")) {
            builder.addVendorDir(value);
        }
        final List<String> modules = strings(object, "modules");
        if (modules.isEmpty()) {
            builder.addModule(metadata.getId());
        } else {
            for (final String module : modules) {
                builder.addModule(module);
            }
        }
        return builder.build();
    }

    /** The side this JVM runs: {@code client} or {@code server}. */
    public static PyFm.Side currentSide() {
        return FabricLoader.getInstance().getEnvironmentType() == EnvType.CLIENT
                ? PyFm.Side.CLIENT : PyFm.Side.SERVER;
    }

    private static Path sourceOf(final ModContainer mod) {
        final ModOrigin origin = mod.getOrigin();
        if (origin == null) {
            return null;
        }
        final List<Path> paths = origin.getPaths();
        return paths == null || paths.isEmpty() ? null : paths.get(0);
    }

    private static String string(final CustomValue.CvObject object, final String key,
                                 final String fallback) {
        try {
            if (object.containsKey(key)) {
                return object.get(key).getAsString();
            }
        } catch (final RuntimeException exception) {
            PyFm.log().warn("{} ignoring unreadable '{}': {}", PyFm.LOG_PREFIX, key,
                    exception.toString());
        }
        return fallback;
    }

    private static List<String> strings(final CustomValue.CvObject object, final String key) {
        try {
            if (!object.containsKey(key)) {
                return List.of();
            }
            final CustomValue.CvArray array = object.get(key).getAsArray();
            final java.util.List<String> values = new java.util.ArrayList<>();
            for (int index = 0; index < array.size(); index++) {
                values.add(array.get(index).getAsString());
            }
            return values;
        } catch (final RuntimeException exception) {
            PyFm.log().warn("{} ignoring unreadable '{}': {}", PyFm.LOG_PREFIX, key,
                    exception.toString());
            return List.of();
        }
    }
}

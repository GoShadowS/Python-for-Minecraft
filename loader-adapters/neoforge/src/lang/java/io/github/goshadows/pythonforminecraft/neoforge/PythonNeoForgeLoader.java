/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import java.util.Collection;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmException;
import io.github.goshadows.pythonforminecraft.core.PythonModDescriptor;
import io.github.goshadows.pythonforminecraft.core.PythonModInstance;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.ModLoadingException;
import net.neoforged.fml.ModLoadingIssue;
import net.neoforged.neoforgespi.IIssueReporting;
import net.neoforged.neoforgespi.language.IModInfo;
import net.neoforged.neoforgespi.language.IModLanguageLoader;
import net.neoforged.neoforgespi.language.ModFileScanData;
import net.neoforged.neoforgespi.locating.IModFile;

/**
 * The NeoForge mod loader for Python mods.
 *
 * <p>Registered through
 * {@code META-INF/services/net.neoforged.neoforgespi.language.IModLanguageLoader} and
 * selected by a Python mod with {@code modLoader = "pythonforminecraft"} plus
 * {@code loaderVersion = "[1,)"}. The jar carrying this class must have the manifest
 * attribute {@code FMLModType: LIBRARY} so that FML loads it on the plugin layer — the same
 * mechanism Kotlin for Forge uses for {@code modLoader = "kotlinforforge"}.</p>
 */
public final class PythonNeoForgeLoader implements IModLanguageLoader {

    @Override
    public String name() {
        return PyFm.NEOFORGE_LOADER;
    }

    @Override
    public String version() {
        final String fromManifest = getClass().getPackage().getImplementationVersion();
        return fromManifest == null ? PyFm.VERSION : fromManifest;
    }

    @Override
    public ModContainer loadMod(final IModInfo info, final ModFileScanData scanResults,
                                final ModuleLayer layer) {
        final PythonModDescriptor descriptor;
        final PythonModInstance instance;
        try {
            descriptor = NeoForgePythonMods.describe(info);
            instance = NeoForgePythonMods.create(descriptor);
        } catch (final PyFmException exception) {
            PyFm.log().error("{}", exception.getMessage());
            throw new ModLoadingException(ModLoadingIssue
                    .error("fml.modloadingissue.failedtoloadmod")
                    .withCause(exception)
                    .withAffectedMod(info));
        }
        PyFm.log().info("{} Python mod '{}' ({}) loaded by the {} loader on the {} side; "
                        + "entry points: {}", PyFm.LOG_PREFIX, descriptor.modId(),
                descriptor.version(), name(), descriptor.side().id(),
                descriptor.entrypoints());
        return new PythonModContainer(info, instance);
    }

    @Override
    public void validate(final IModFile file, final Collection<ModContainer> loadedContainers,
                         final IIssueReporting reporter) {
        for (final IModInfo info : file.getModInfos()) {
            if (info.getLoader() != this) {
                continue;
            }
            final boolean hasEntrypoint = info.getModProperties().containsKey(
                            NeoForgePythonMods.KEY_MAIN)
                    || info.getModProperties().containsKey(NeoForgePythonMods.KEY_CLIENT)
                    || info.getModProperties().containsKey(NeoForgePythonMods.KEY_SERVER);
            if (!hasEntrypoint) {
                reporter.addIssue(ModLoadingIssue
                        .warning("fml.modloadingissue.missingpythonentrypoint",
                                info.getModId())
                        .withAffectedModFile(file));
            }
        }
    }
}

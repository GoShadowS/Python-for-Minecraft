/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.fabric;

import java.lang.reflect.Proxy;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmException;
import io.github.goshadows.pythonforminecraft.core.PythonEntrypoints;
import io.github.goshadows.pythonforminecraft.core.PythonModInstance;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.DedicatedServerModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.loader.api.LanguageAdapter;
import net.fabricmc.loader.api.LanguageAdapterException;
import net.fabricmc.loader.api.ModContainer;

/**
 * The Fabric language adapter that makes {@code "adapter": "python"} work.
 *
 * <p>Declared by the core artifact in its own {@code fabric.mod.json}:
 * <pre>{@code
 * "languageAdapters": {
 *     "python": "io.github.goshadows.pythonforminecraft.fabric.PythonLanguageAdapter"
 * }
 * }</pre>
 * This is the exact mechanism Fabric Language Kotlin uses for {@code "adapter": "kotlin"}.</p>
 */
public final class PythonLanguageAdapter implements LanguageAdapter {

    @Override
    public <T> T create(final ModContainer mod, final String value, final Class<T> type)
            throws LanguageAdapterException {
        final String modId = mod.getMetadata().getId();
        final PyFm.Phase phase = phaseFor(type, modId);
        PythonEntrypoints.validate(value, modId);
        final PythonModInstance instance;
        try {
            instance = FabricPythonMods.getOrCreate(mod);
        } catch (final PyFmException exception) {
            throw new LanguageAdapterException(exception.getMessage(), exception);
        }
        final Object proxy = Proxy.newProxyInstance(type.getClassLoader(),
                new Class<?>[] {type},
                new PythonEntrypointHandler(instance, phase, value.trim()));
        return type.cast(proxy);
    }

    /** Maps the entry point interface Fabric asked for onto a Python lifecycle phase. */
    private static PyFm.Phase phaseFor(final Class<?> type, final String modId) {
        if (ClientModInitializer.class.equals(type)) {
            return PyFm.Phase.CLIENT_INITIALIZE;
        }
        if (DedicatedServerModInitializer.class.equals(type)) {
            return PyFm.Phase.SERVER_INITIALIZE;
        }
        if (ModInitializer.class.equals(type)) {
            return PyFm.Phase.INITIALIZE;
        }
        throw new PyFmException("entry point type " + type.getName()
                + " is not supported; use main, client or server with adapter 'python'",
                modId, "entrypoint");
    }
}

/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PyFmException;
import io.github.goshadows.pythonforminecraft.core.PythonModInstance;
import net.neoforged.bus.api.BusBuilder;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.event.IModBusEvent;
import net.neoforged.neoforgespi.language.IModInfo;

/**
 * The NeoForge mod container of a Python mod.
 *
 * <p>Created by {@link PythonNeoForgeLoader}. Running the Python entry points happens in
 * {@link #constructMod()}, which is where NeoForge expects a mod to be built; a Python
 * failure is rethrown so NeoForge reports the mod as failed instead of loaded.</p>
 */
public final class PythonModContainer extends ModContainer {

    private final IEventBus eventBus;
    private final PythonModInstance instance;

    public PythonModContainer(final IModInfo info, final PythonModInstance instance) {
        super(info);
        this.instance = instance;
        this.eventBus = BusBuilder.builder()
                .markerType(IModBusEvent.class)
                .build();
    }

    /** The Python mod this container runs. */
    public PythonModInstance pythonMod() {
        return this.instance;
    }

    @Override
    public IEventBus getEventBus() {
        return this.eventBus;
    }

    @Override
    protected void constructMod() {
        final PyFm.Side side = NeoForgePythonMods.currentSide();
        try {
            this.instance.bootstrap();
            this.instance.runPhase(PyFm.Phase.INITIALIZE);
            this.instance.runPhase(side == PyFm.Side.CLIENT
                    ? PyFm.Phase.CLIENT_INITIALIZE : PyFm.Phase.SERVER_INITIALIZE);
        } catch (final PyFmException exception) {
            PyFm.log().error("{}", exception.getMessage());
            throw exception;
        }
    }
}

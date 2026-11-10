/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.fabric;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.util.concurrent.atomic.AtomicBoolean;

import io.github.goshadows.pythonforminecraft.core.PyFm;
import io.github.goshadows.pythonforminecraft.core.PythonModInstance;

/**
 * Implements a Fabric entry point interface ({@code ModInitializer},
 * {@code ClientModInitializer}, {@code DedicatedServerModInitializer}) by running a Python
 * entry point.
 *
 * <p>Fabric's entry point interfaces are single-method interfaces, so a dynamic proxy is
 * enough; nothing here needs Truffle to implement a Java interface from Python.</p>
 */
final class PythonEntrypointHandler implements InvocationHandler {

    private final PythonModInstance instance;
    private final PyFm.Phase phase;
    private final String spec;
    private final AtomicBoolean ran = new AtomicBoolean();

    PythonEntrypointHandler(final PythonModInstance instance, final PyFm.Phase phase,
                            final String spec) {
        this.instance = instance;
        this.phase = phase;
        this.spec = spec;
    }

    @Override
    public Object invoke(final Object proxy, final Method method, final Object[] args) {
        final String name = method.getName();
        if ("toString".equals(name)) {
            return "PythonEntrypoint[" + this.instance.descriptor().modId() + " "
                    + this.phase.id() + " " + this.spec + "]";
        }
        if ("hashCode".equals(name)) {
            return System.identityHashCode(proxy);
        }
        if ("equals".equals(name)) {
            return proxy == (args == null ? null : args[0]);
        }
        if (this.ran.compareAndSet(false, true)) {
            PyFm.log().info("{} running Python entry point {} of '{}' for phase {}",
                    PyFm.LOG_PREFIX, this.spec, this.instance.descriptor().modId(),
                    this.phase.id());
            this.instance.runPhase(this.phase, this.spec);
        }
        return null;
    }
}

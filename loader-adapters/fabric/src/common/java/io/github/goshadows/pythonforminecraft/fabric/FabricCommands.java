/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.fabric;

import java.util.List;

import com.mojang.brigadier.CommandDispatcher;

import io.github.goshadows.pythonforminecraft.core.CommandSpec;
import io.github.goshadows.pythonforminecraft.core.Commands;
import io.github.goshadows.pythonforminecraft.core.PyFm;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;

/**
 * Registers the commands Python mods declared, using Fabric API's command callback and
 * Brigadier directly.
 */
public final class FabricCommands {

    private FabricCommands() {
    }

    /** Installs the registrar and the reply implementation. Idempotent. */
    public static void install() {
        if (Commands.registrar() != null) {
            return;
        }
        Commands.setReplier((source, text) -> {
            if (source instanceof CommandSourceStack stack) {
                stack.sendSuccess(() -> Component.literal(text), false);
            } else {
                PyFm.log().warn("{} cannot reply to source {}: {}", PyFm.LOG_PREFIX, source,
                        text);
            }
        });
        Commands.setRegistrar(new Registrar());
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            for (final CommandSpec spec : Commands.specs()) {
                register(dispatcher, spec);
            }
        });
    }

    private static void register(final CommandDispatcher<CommandSourceStack> dispatcher,
                                 final CommandSpec spec) {
        dispatcher.register(net.minecraft.commands.Commands.literal(spec.name())
                .requires(source -> source.hasPermission(spec.permission()))
                .executes(context -> {
                    final boolean handled = Commands.dispatch(spec.key(), context.getSource(),
                            List.of());
                    if (!handled) {
                        context.getSource().sendFailure(Component.literal(
                                "Python command /" + spec.name() + " is not available"));
                        return 0;
                    }
                    return com.mojang.brigadier.Command.SINGLE_SUCCESS;
                }));
        PyFm.log().info("{} /{} registered for Python mod '{}'", PyFm.LOG_PREFIX, spec.name(),
                spec.modId());
    }

    private static final class Registrar implements io.github.goshadows.pythonforminecraft
            .core.CommandRegistrar {

        @Override
        public void register(final CommandSpec spec) {
            // Fabric builds its command tree when the server starts; the specs are picked up
            // by the CommandRegistrationCallback registered in install().
            PyFm.log().debug("{} command /{} queued for the next command registration",
                    PyFm.LOG_PREFIX, spec.name());
        }

        @Override
        public String loader() {
            return "fabric";
        }
    }
}

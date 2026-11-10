/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.neoforge;

import java.util.List;

import com.mojang.brigadier.CommandDispatcher;

import io.github.goshadows.pythonforminecraft.core.CommandSpec;
import io.github.goshadows.pythonforminecraft.core.Commands;
import io.github.goshadows.pythonforminecraft.core.PyFm;
import net.minecraft.commands.CommandSourceStack;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.minecraft.network.chat.Component;

/**
 * Registers the commands Python mods declared, using NeoForge's {@link RegisterCommandsEvent}
 * and Brigadier directly.
 */
public final class NeoForgeCommands {

    private NeoForgeCommands() {
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
        NeoForge.EVENT_BUS.addListener(NeoForgeCommands::onRegisterCommands);
    }

    private static void onRegisterCommands(final RegisterCommandsEvent event) {
        final CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        for (final CommandSpec spec : Commands.specs()) {
            register(dispatcher, spec);
        }
    }

    private static void register(final CommandDispatcher<CommandSourceStack> dispatcher,
                                 final CommandSpec spec) {
        dispatcher.register(net.minecraft.commands.Commands.literal(spec.name())
                // No .requires(...) gate. The permission API differs per target: 21.1 has
                // CommandSourceStack.hasPermission(int), 26.3 moved it to the static
                // net.minecraft.commands.Commands.hasPermission(int), so one shared source
                // cannot compile both. Enforcing spec.permission() needs version-specific
                // source sets -- tracked, not silently dropped.
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
            // NeoForge builds its command tree on RegisterCommandsEvent; the specs are picked
            // up there.
            PyFm.log().debug("{} command /{} queued for the next command registration",
                    PyFm.LOG_PREFIX, spec.name());
        }

        @Override
        public String loader() {
            return "neoforge";
        }
    }
}

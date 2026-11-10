/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Constants, the side/phase enums and the logger of Python-for-Minecraft.
 *
 * <p>This class is loader-agnostic: it never touches Fabric, NeoForge or Minecraft types,
 * which is what keeps the core jar free of client classes and loadable on a dedicated
 * server.</p>
 */
public final class PyFm {

    /** Version of Python-for-Minecraft. Kept in sync with gradle.properties. */
    public static final String VERSION = "1.0.0";

    /** Mod id of the core artifact: the language provider itself. */
    public static final String CORE_MOD_ID = "pythonforminecraft_core";

    /** Mod id of the client artifact. */
    public static final String CLIENT_MOD_ID = "pythonforminecraft";

    /** Mod id of the server-capable artifact. */
    public static final String SERVER_MOD_ID = "pythonforminecraft_server";

    /** Name of the Fabric language adapter, used as {@code "adapter": "python"}. */
    public static final String FABRIC_ADAPTER = "python";

    /** Name of the NeoForge mod loader, used as {@code modLoader = "pythonforminecraft"}. */
    public static final String NEOFORGE_LOADER = "pythonforminecraft";

    /** Truffle language id. */
    public static final String LANGUAGE = "python";

    /** Log prefix of every message this project writes. */
    public static final String LOG_PREFIX = "[PyFM]";

    /** GraalPy version the build pins, for log lines and diagnostics. */
    public static final String GRAALPY_VERSION = "25.5.5";

    private static final Logger LOGGER = LoggerFactory.getLogger("PythonForMinecraft");

    private PyFm() {
    }

    public static Logger log() {
        return LOGGER;
    }

    /** The physical side a component runs on. */
    public enum Side {
        CLIENT("client"),
        SERVER("server");

        private final String id;

        Side(final String id) {
            this.id = id;
        }

        /** The identifier used by the Python side ({@code "client"} / {@code "server"}). */
        public String id() {
            return this.id;
        }

        public static Side of(final String value) {
            for (final Side side : values()) {
                if (side.id.equalsIgnoreCase(value)) {
                    return side;
                }
            }
            throw new IllegalArgumentException("unknown side: " + value);
        }
    }

    /** The three lifecycle phases a Python entry point can be invoked for. */
    public enum Phase {
        /** Common code, both sides. Python hook: {@code on_initialize}. */
        INITIALIZE("initialize"),
        /** Client only. Python hook: {@code on_client_initialize}. */
        CLIENT_INITIALIZE("client_initialize"),
        /** Dedicated server only. Python hook: {@code on_server_initialize}. */
        SERVER_INITIALIZE("server_initialize");

        private final String id;

        Phase(final String id) {
            this.id = id;
        }

        public String id() {
            return this.id;
        }

        /** True when this phase may run on {@code side}. */
        public boolean runsOn(final Side side) {
            return switch (this) {
                case INITIALIZE -> true;
                case CLIENT_INITIALIZE -> side == Side.CLIENT;
                case SERVER_INITIALIZE -> side == Side.SERVER;
            };
        }
    }
}

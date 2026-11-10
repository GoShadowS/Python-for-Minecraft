/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Loader-neutral description of one Python mod.
 *
 * <p>Fabric builds it from {@code fabric.mod.json} (entry points with the {@code python}
 * adapter plus a {@code custom.pythonforminecraft} block); NeoForge builds it from
 * {@code neoforge.mods.toml} ({@code modLoader = "pythonforminecraft"} plus
 * {@code [modproperties.<modId>]}). The two loaders really do differ, and this record is
 * where the difference stops.</p>
 */
public final class PythonModDescriptor {

    private final String modId;
    private final PyFm.Side side;
    private final String displayName;
    private final String version;
    private final String pythonRoot;
    private final List<String> vendorDirs;
    private final List<String> modules;
    private final Map<PyFm.Phase, String> entrypoints;
    private final Path source;

    private PythonModDescriptor(final Builder builder) {
        this.modId = Objects.requireNonNull(builder.modId, "modId");
        this.side = Objects.requireNonNull(builder.side, "side");
        this.displayName = builder.displayName == null ? builder.modId : builder.displayName;
        this.version = builder.version == null ? "0.0.0" : builder.version;
        this.pythonRoot = builder.pythonRoot == null ? "python" : builder.pythonRoot;
        this.vendorDirs = List.copyOf(builder.vendorDirs);
        this.modules = List.copyOf(builder.modules);
        this.entrypoints = Collections.unmodifiableMap(new EnumMap<>(builder.entrypoints));
        this.source = builder.source;
    }

    public String modId() {
        return this.modId;
    }

    public PyFm.Side side() {
        return this.side;
    }

    public String displayName() {
        return this.displayName;
    }

    public String version() {
        return this.version;
    }

    /** Path of the Python sources inside the mod jar, e.g. {@code python}. */
    public String pythonRoot() {
        return this.pythonRoot;
    }

    /** Directories inside the mod jar that hold vendored dependencies. */
    public List<String> vendorDirs() {
        return this.vendorDirs;
    }

    /** Packages to import at bootstrap so that decorators register themselves. */
    public List<String> modules() {
        return this.modules;
    }

    public Map<PyFm.Phase, String> entrypoints() {
        return this.entrypoints;
    }

    public String entrypoint(final PyFm.Phase phase) {
        return this.entrypoints.get(phase);
    }

    public boolean hasEntrypoint(final PyFm.Phase phase) {
        return this.entrypoints.containsKey(phase);
    }

    /** Jar file or source directory the mod was found in. */
    public Path source() {
        return this.source;
    }

    public static Builder builder(final String modId, final PyFm.Side side) {
        return new Builder(modId, side);
    }

    @Override
    public String toString() {
        return "PythonModDescriptor[" + this.modId + " " + this.version + " side="
                + this.side.id() + " entrypoints=" + this.entrypoints + "]";
    }

    /** Mutable builder; loader adapters use it while parsing metadata. */
    public static final class Builder {

        private final String modId;
        private final PyFm.Side side;
        private final List<String> vendorDirs = new ArrayList<>();
        private final List<String> modules = new ArrayList<>();
        private final Map<PyFm.Phase, String> entrypoints = new LinkedHashMap<>();
        private String displayName;
        private String version;
        private String pythonRoot;
        private Path source;

        private Builder(final String modId, final PyFm.Side side) {
            this.modId = modId;
            this.side = side;
        }

        public Builder displayName(final String value) {
            this.displayName = value;
            return this;
        }

        public Builder version(final String value) {
            this.version = value;
            return this;
        }

        public Builder pythonRoot(final String value) {
            this.pythonRoot = value;
            return this;
        }

        public Builder source(final Path value) {
            this.source = value;
            return this;
        }

        public Builder addVendorDir(final String value) {
            if (value != null && !value.isBlank()) {
                this.vendorDirs.add(value.trim());
            }
            return this;
        }

        public Builder addModule(final String value) {
            if (value != null && !value.isBlank()) {
                this.modules.add(value.trim());
            }
            return this;
        }

        public Builder entrypoint(final PyFm.Phase phase, final String spec) {
            if (spec != null && !spec.isBlank()) {
                PythonEntrypoints.validate(spec, this.modId);
                this.entrypoints.put(phase, spec.trim());
            }
            return this;
        }

        public PythonModDescriptor build() {
            return new PythonModDescriptor(this);
        }
    }
}

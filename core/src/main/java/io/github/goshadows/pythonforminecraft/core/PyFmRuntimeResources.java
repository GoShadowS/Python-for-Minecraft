/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.io.IOException;
import java.io.InputStream;
import java.net.URISyntaxException;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Enumeration;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;

/**
 * Unpacks the {@code pfm} Python package that ships inside the core jar.
 *
 * <p>Python mods {@code import pfm}, so the package has to be a real directory on
 * {@code sys.path}. It is stored in the core jar under {@link #RESOURCE_ROOT} and unpacked
 * once per version into {@code <workDir>/runtime/<version>}; the directory is put on
 * {@code sys.path} ahead of the mod's own sources, so a mod cannot accidentally shadow the
 * runtime package.</p>
 */
public final class PyFmRuntimeResources {

    /** Location of the {@code pfm} package inside the core jar. */
    public static final String RESOURCE_ROOT = "pythonforminecraft/";

    private PyFmRuntimeResources() {
    }

    /**
     * @return the directory to put on {@code sys.path} for the runtime package
     */
    public static Path ensure(final Path workDir) throws IOException {
        final Path target = workDir.resolve("runtime").resolve(PyFm.VERSION);
        final Path marker = target.resolve(".pyfm-runtime");
        if (Files.isRegularFile(marker)) {
            return target;
        }
        final Path jar = coreJar();
        Files.createDirectories(target);
        if (jar == null) {
            // Development environment: the resources are on the class path as a directory.
            PyFm.log().warn("{} no core jar found; relying on the class path for the pfm "
                    + "package (development mode)", PyFm.LOG_PREFIX);
            Files.writeString(marker, "classpath");
            return target;
        }
        int count = 0;
        try (JarFile jarFile = new JarFile(jar.toFile())) {
            final Enumeration<JarEntry> entries = jarFile.entries();
            while (entries.hasMoreElements()) {
                final JarEntry entry = entries.nextElement();
                final String name = entry.getName();
                if (entry.isDirectory() || !name.startsWith(RESOURCE_ROOT)) {
                    continue;
                }
                final String relative = name.substring(RESOURCE_ROOT.length());
                if (relative.isEmpty()) {
                    continue;
                }
                final Path out = target.resolve(relative).normalize();
                if (!out.startsWith(target)) {
                    throw new IOException("refusing to extract '" + name + "' outside " + target);
                }
                Files.createDirectories(out.getParent());
                try (InputStream in = jarFile.getInputStream(entry)) {
                    Files.copy(in, out, StandardCopyOption.REPLACE_EXISTING);
                }
                count++;
            }
        }
        Files.writeString(marker, String.valueOf(count));
        PyFm.log().info("{} unpacked the pfm package ({} files) into {}", PyFm.LOG_PREFIX, count,
                target);
        return target;
    }

    /** The jar this class was loaded from, or {@code null} in a development environment. */
    static Path coreJar() {
        try {
            final URL location = PyFm.class.getProtectionDomain().getCodeSource() == null
                    ? null : PyFm.class.getProtectionDomain().getCodeSource().getLocation();
            if (location == null) {
                return null;
            }
            final Path path = Path.of(location.toURI());
            return Files.isRegularFile(path) ? path : null;
        } catch (final URISyntaxException | RuntimeException exception) {
            PyFm.log().warn("{} cannot locate the core jar: {}", PyFm.LOG_PREFIX,
                    exception.toString());
            return null;
        }
    }
}

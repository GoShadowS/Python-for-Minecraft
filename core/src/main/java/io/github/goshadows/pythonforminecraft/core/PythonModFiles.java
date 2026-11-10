/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HexFormat;
import java.util.List;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;

/**
 * Makes the Python sources of a mod readable from the file system.
 *
 * <p>Python imports from directories, not from mod jars, so the tree below
 * {@code pythonRoot} is unpacked into {@code <game>/pythonforminecraft/<modId>/<hash>} and
 * that directory goes on {@code sys.path}. The hash is the sha256 of the mod jar, so an
 * updated jar unpacks into a new directory and a stale cache is never reused.</p>
 *
 * <p>In a development environment {@code pythonRoot} may point at an existing directory;
 * it is then used as-is.</p>
 */
public final class PythonModFiles {

    private static final String MARKER = ".pyfm-extracted";

    private PythonModFiles() {
    }

    /**
     * @return the directory that must be put on {@code sys.path} for *descriptor*
     */
    public static Path pythonPath(final PythonModDescriptor descriptor, final Path workDir)
            throws IOException {
        final Path source = descriptor.source();
        if (source == null) {
            throw new PyFmException("no source location is known for this Python mod",
                    descriptor.modId(), "unpack");
        }
        if (Files.isDirectory(source)) {
            final Path inPlace = source.resolve(descriptor.pythonRoot());
            if (Files.isDirectory(inPlace)) {
                return inPlace;
            }
            throw new PyFmException("no '" + descriptor.pythonRoot()
                    + "' directory under " + source, descriptor.modId(), "unpack");
        }
        if (!Files.isRegularFile(source)) {
            throw new PyFmException("source is neither a file nor a directory: " + source,
                    descriptor.modId(), "unpack");
        }
        final String hash = sha256(source).substring(0, 16);
        final Path target = workDir.resolve(descriptor.modId()).resolve(hash);
        final Path marker = target.resolve(MARKER);
        if (Files.isRegularFile(marker)) {
            return target;
        }
        extract(source, descriptor.pythonRoot(), target);
        for (final String vendor : descriptor.vendorDirs()) {
            extract(source, vendor, target.resolve("vendor"));
        }
        Files.writeString(marker, hash, StandardCharsets.UTF_8);
        return target;
    }

    /** Absolute vendor directories to put on {@code sys.path}. */
    public static List<String> vendorPaths(final PythonModDescriptor descriptor,
                                           final Path pythonDir) {
        final List<String> paths = new ArrayList<>();
        if (!descriptor.vendorDirs().isEmpty()) {
            paths.add(pythonDir.resolve("vendor").toAbsolutePath().toString());
        }
        return paths;
    }

    /** Extracts every jar entry under *prefix* into *target*, relativised. */
    static void extract(final Path jar, final String prefix, final Path target)
            throws IOException {
        final String needle = normalise(prefix);
        Files.createDirectories(target);
        try (JarFile jarFile = new JarFile(jar.toFile())) {
            final Enumeration<JarEntry> entries = jarFile.entries();
            while (entries.hasMoreElements()) {
                final JarEntry entry = entries.nextElement();
                if (entry.isDirectory()) {
                    continue;
                }
                final String name = normalise(entry.getName());
                if (!name.startsWith(needle) || name.equals(needle)) {
                    continue;
                }
                final String relative = name.substring(needle.length());
                if (relative.isEmpty() || relative.endsWith("/")) {
                    continue;
                }
                final Path out = safeResolve(target, relative);
                Files.createDirectories(out.getParent());
                try (InputStream in = jarFile.getInputStream(entry)) {
                    Files.copy(in, out, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                }
            }
        }
    }

    /** Blocks zip-slip: an entry must never escape the target directory. */
    private static Path safeResolve(final Path target, final String relative)
            throws IOException {
        final Path resolved = target.resolve(relative).normalize();
        if (!resolved.startsWith(target)) {
            throw new IOException("refusing to extract '" + relative
                    + "' outside of " + target);
        }
        return resolved;
    }

    private static String normalise(final String path) {
        String value = path.replace('\\', '/');
        if (!value.endsWith("/")) {
            value = value + "/";
        }
        return value.startsWith("/") ? value.substring(1) : value;
    }

    private static String sha256(final Path file) throws IOException {
        final MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (final NoSuchAlgorithmException exception) {
            throw new IOException("SHA-256 is unavailable", exception);
        }
        try (InputStream in = Files.newInputStream(file)) {
            final byte[] buffer = new byte[1 << 16];
            int read;
            while ((read = in.read(buffer)) > 0) {
                digest.update(buffer, 0, read);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }
}

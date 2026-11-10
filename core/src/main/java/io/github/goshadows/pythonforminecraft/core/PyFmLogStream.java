/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Routes Python's {@code print()} output line by line into the game log.
 *
 * <p>Used as the {@code stdout}/{@code stderr} of every Python context, so a stray
 * {@code print()} in a Python mod still shows the mod id it came from.</p>
 */
public final class PyFmLogStream extends java.io.OutputStream {

    private final ByteArrayOutputStream buffer = new ByteArrayOutputStream();
    private final String modId;
    private final boolean error;

    PyFmLogStream(final String modId, final boolean error) {
        this.modId = modId;
        this.error = error;
    }

    @Override
    public synchronized void write(final int value) {
        if (value == '\n') {
            flushLine();
        } else {
            this.buffer.write(value);
        }
    }

    @Override
    public synchronized void write(final byte[] bytes, final int offset, final int length) {
        for (int index = offset; index < offset + length; index++) {
            write(bytes[index]);
        }
    }

    @Override
    public synchronized void flush() {
        if (this.buffer.size() > 0) {
            flushLine();
        }
    }

    private void flushLine() {
        final String line = this.buffer.toString(StandardCharsets.UTF_8).stripTrailing();
        this.buffer.reset();
        if (line.isEmpty()) {
            return;
        }
        if (this.error) {
            PyFm.log().error("{} '{}' (python) {}", PyFm.LOG_PREFIX, this.modId, line);
        } else {
            PyFm.log().info("{} '{}' (python) {}", PyFm.LOG_PREFIX, this.modId, line);
        }
    }
}

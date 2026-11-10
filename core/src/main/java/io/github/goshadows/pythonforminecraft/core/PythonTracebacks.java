/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import org.graalvm.polyglot.PolyglotException;
import org.graalvm.polyglot.SourceSection;
import org.graalvm.polyglot.Value;

/**
 * Turns a {@link PolyglotException} into the report Python-for-Minecraft promises:
 * mod id, phase, file, line and a usable Python traceback.
 */
public final class PythonTracebacks {

    private PythonTracebacks() {
    }

    /**
     * Formats *exception*. When *runtime* is given and the failure happened in Python, the
     * traceback is produced by Python's own {@code traceback} module through
     * {@code pfm._format_guest_exception}; otherwise the polyglot message is used.
     */
    public static String format(final PolyglotException exception, final String modId,
                                final String phase, final PythonRuntime runtime) {
        final StringBuilder builder = new StringBuilder();
        builder.append(PyFm.LOG_PREFIX).append(" Python mod '").append(modId)
                .append("' failed");
        if (phase != null) {
            builder.append(" during ").append(phase);
        }
        final SourceSection location = exception.getSourceLocation();
        if (location != null) {
            final String name = location.getSource() != null
                    ? location.getSource().getName() : "<python>";
            builder.append("\n  at ").append(name).append(':').append(location.getStartLine());
        }
        if (exception.isHostException()) {
            final Throwable host = exception.asHostException();
            builder.append("\n  host exception: ")
                    .append(host == null ? "unknown" : host.toString());
            return builder.toString();
        }
        final String guest = guestTraceback(exception, modId, phase, runtime);
        builder.append('\n').append(indent(guest));
        return builder.toString();
    }

    /** Wraps *exception* into a {@link PyFmException} so loaders report a failed mod. */
    public static PyFmException toException(final PolyglotException exception,
                                            final String modId, final String phase,
                                            final PythonRuntime runtime) {
        return new PyFmException(format(exception, modId, phase, runtime), modId, phase,
                exception.isHostException() ? exception.asHostException() : exception);
    }

    private static String guestTraceback(final PolyglotException exception,
                                         final String modId, final String phase,
                                         final PythonRuntime runtime) {
        final Value guest = safeGuestObject(exception);
        if (runtime != null && guest != null && !guest.isNull() && !runtime.isClosed()) {
            try {
                final Value formatted = runtime.call("_format_guest_exception", guest, modId,
                        phase);
                if (formatted != null && !formatted.isNull()) {
                    return formatted.asString();
                }
            } catch (final RuntimeException ignored) {
                // Fall through to the polyglot message; never lose the original failure.
                PyFm.log().debug("{} could not ask Python for a traceback: {}",
                        PyFm.LOG_PREFIX, ignored.toString());
            }
        }
        final String message = exception.getMessage();
        return message == null ? exception.toString() : message;
    }

    private static Value safeGuestObject(final PolyglotException exception) {
        try {
            return exception.getGuestObject();
        } catch (final RuntimeException ignored) {
            return null;
        }
    }

    private static String indent(final String text) {
        final StringBuilder builder = new StringBuilder();
        for (final String line : text.split("\n", -1)) {
            builder.append("  ").append(line).append('\n');
        }
        return builder.toString().stripTrailing();
    }
}

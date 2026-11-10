/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.util.Collection;
import java.util.Map;

/**
 * A very small JSON writer.
 *
 * <p>The Java -&gt; Python protocol passes configuration as JSON text, because a string
 * crosses the polyglot boundary without depending on Truffle's collection conversions.
 * Core deliberately has no JSON library dependency, so it writes the handful of shapes it
 * needs itself.</p>
 */
public final class Json {

    private Json() {
    }

    public static String quote(final String value) {
        if (value == null) {
            return "null";
        }
        final StringBuilder builder = new StringBuilder(value.length() + 2).append('"');
        for (int index = 0; index < value.length(); index++) {
            final char character = value.charAt(index);
            switch (character) {
                case '"' -> builder.append("\\\"");
                case '\\' -> builder.append("\\\\");
                case '\n' -> builder.append("\\n");
                case '\r' -> builder.append("\\r");
                case '\t' -> builder.append("\\t");
                default -> {
                    if (character < 0x20) {
                        builder.append(String.format("\\u%04x", (int) character));
                    } else {
                        builder.append(character);
                    }
                }
            }
        }
        return builder.append('"').toString();
    }

    public static String array(final Collection<String> values) {
        final StringBuilder builder = new StringBuilder("[");
        boolean first = true;
        for (final String value : values) {
            if (!first) {
                builder.append(',');
            }
            builder.append(quote(value));
            first = false;
        }
        return builder.append(']').toString();
    }

    public static String object(final Map<String, String> quotedValues) {
        final StringBuilder builder = new StringBuilder("{");
        boolean first = true;
        for (final Map.Entry<String, String> entry : quotedValues.entrySet()) {
            if (!first) {
                builder.append(',');
            }
            builder.append(quote(entry.getKey())).append(':').append(entry.getValue());
            first = false;
        }
        return builder.append('}').toString();
    }
}

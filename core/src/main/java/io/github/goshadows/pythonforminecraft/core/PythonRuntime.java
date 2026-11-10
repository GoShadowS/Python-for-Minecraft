/*
 * Python-for-Minecraft
 * SPDX-License-Identifier: Apache-2.0
 */
package io.github.goshadows.pythonforminecraft.core;

import java.io.OutputStream;
import java.util.Objects;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Function;

import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Engine;
import org.graalvm.polyglot.Value;

/**
 * One GraalPy context belonging to one Python mod.
 *
 * <p>A Truffle context is not safe for concurrent use, while Minecraft has a client thread
 * and (in single player) an integrated server thread. Every interaction therefore goes
 * through {@link #enter(Function)}, which serialises access with a lock and balances
 * {@link Context#enter()} / {@link Context#leave()} on the calling thread.</p>
 */
public final class PythonRuntime implements AutoCloseable {

    private final Engine engine;
    private final Context context;
    private final ReentrantLock lock = new ReentrantLock();
    private final String modId;
    private volatile Value pfmModule;
    private volatile boolean closed;
    private volatile Thread affinity;

    private PythonRuntime(final Engine engine, final Context context, final String modId) {
        this.engine = Objects.requireNonNull(engine, "engine");
        this.context = Objects.requireNonNull(context, "context");
        this.modId = Objects.requireNonNull(modId, "modId");
    }

    /**
     * Creates the shared engine. One engine per JVM is enough: a dedicated server JVM only
     * runs server code, and a client JVM runs the client plus, in single player, the
     * integrated server.
     */
    public static Engine newEngine() {
        return Engine.newBuilder()
                .option("engine.WarnInterpreterOnly", "false")
                .build();
    }

    /**
     * Creates a context for *modId*. Python's own {@code stdout}/{@code stderr} are routed
     * into the game log through *out*/*err* when provided.
     */
    public static PythonRuntime create(final Engine engine, final String modId,
                                       final PyFmConfig config, final OutputStream out,
                                       final OutputStream err) {
        final Context.Builder builder = Context.newBuilder(PyFm.LANGUAGE)
                .engine(engine)
                .allowAllAccess(config.allowAllAccess())
                .option("engine.WarnInterpreterOnly", "false");
        if (out != null) {
            builder.out(out);
        }
        if (err != null) {
            builder.err(err);
        }
        return new PythonRuntime(engine, builder.build(), modId);
    }

    public String modId() {
        return this.modId;
    }

    public Engine engine() {
        return this.engine;
    }

    public boolean isClosed() {
        return this.closed;
    }

    /**
     * Runs *body* with exclusive, entered access to the context.
     *
     * @throws PyFmException when the runtime is already closed
     */
    public <T> T enter(final Function<Context, T> body) {
        ensureOpen();
        this.lock.lock();
        try {
            this.affinity = Thread.currentThread();
            this.context.enter();
            try {
                return body.apply(this.context);
            } finally {
                this.context.leave();
            }
        } finally {
            this.lock.unlock();
        }
    }

    /** {@link #enter(Function)} for bodies without a return value. */
    public void enter(final Runnable body) {
        enter(context -> {
            body.run();
            return null;
        });
    }

    /**
     * The {@code pfm} module of this context, imported on first use.
     *
     * <p>The returned {@link Value} must only be used inside an entered scope; prefer
     * {@link #call(String, Object...)}.</p>
     */
    public Value pfm() {
        return enter(context -> pfmModule());
    }

    /** Calls a member of the {@code pfm} module inside one entered scope. */
    public Value call(final String member, final Object... args) {
        ensureOpen();
        this.lock.lock();
        try {
            this.affinity = Thread.currentThread();
            this.context.enter();
            try {
                return pfmModule().invokeMember(member, args);
            } finally {
                this.context.leave();
            }
        } finally {
            this.lock.unlock();
        }
    }

    /** Evaluates raw Python source; used for diagnostics and tests. */
    public Value eval(final String source, final String name) {
        return enter(context -> context.eval(
                org.graalvm.polyglot.Source.newBuilder(PyFm.LANGUAGE, source, name)
                        .buildLiteral()));
    }

    /**
     * The thread that last used this runtime, or {@code null}.
     *
     * <p>Used to warn when an event arrives on a thread other than the one the mod was
     * initialised on, which is what the loader APIs usually require.</p>
     */
    public Thread affinity() {
        return this.affinity;
    }

    @Override
    public void close() {
        if (this.closed) {
            return;
        }
        this.closed = true;
        try {
            this.lock.lock();
            try {
                this.context.close(true);
            } finally {
                this.lock.unlock();
            }
        } catch (final RuntimeException exception) {
            PyFm.log().warn("{} failed to close the Python context of {}: {}",
                    PyFm.LOG_PREFIX, this.modId, exception.toString());
        }
    }

    private Value pfmModule() {
        Value module = this.pfmModule;
        if (module == null) {
            module = this.context.eval(PyFm.LANGUAGE, "import pfm\npfm");
            this.pfmModule = module;
        }
        return module;
    }

    private void ensureOpen() {
        if (this.closed) {
            throw new PyFmException("the Python runtime is closed", this.modId, null);
        }
    }
}

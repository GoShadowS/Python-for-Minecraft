plugins {
    `java-library`
}

group = "io.github.goshadows"
version = "1.0.0"

java {
    withSourcesJar()
}

// No toolchain block: it would demand a specific installed JDK. Java 21 is
// the bytecode floor for every supported combination, so release is enough.
tasks.withType<JavaCompile>().configureEach {
    options.release.set(21)
}

repositories {
    mavenCentral()
}

dependencies {
    // GraalPy is the Python runtime; see docs/architecture.md.
    api(libs.bundles.graalpy)
    compileOnly(libs.slf4j.api)

    testImplementation(libs.junit.jupiter)
    testImplementation(libs.slf4j.api)
    testRuntimeOnly("org.slf4j:slf4j-simple:$2.0.17")
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("passed", "failed", "skipped")
    }
}

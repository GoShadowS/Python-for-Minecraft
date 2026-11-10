plugins {
    `java-library`
}

group = "io.github.goshadows"
version = "1.0.0"

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
    withSourcesJar()
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

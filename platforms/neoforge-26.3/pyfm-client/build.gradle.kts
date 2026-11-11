plugins {
    id("net.neoforged.moddev")
    alias(libs.plugins.shadow)
}

val neoforge_version: String = project.property("neoforge_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pythonforminecraft-client-neoforge-26.3")
}

// See the fabric builds: shaded dependencies travel inside the core jar.
// Shadow expands every file in this configuration as a ZIP. Created without
// attributes, Gradle resolves it the legacy way, where the artifact of a
// pom-packaging module is the POM file itself -- that is why shadowJar died on
// "Cannot expand ZIP .../python-community-25.5.5.0.3.pom" on every platform.
// With runtime attributes Gradle matches variants instead, so an aggregator POM
// contributes its dependencies (real jars) and no artifact of its own.
val shade: Configuration = configurations.create("shade") {
    isCanBeConsumed = false
    isCanBeResolved = true
    attributes {
        // Fully qualified on purpose: this must not depend on the Kotlin DSL
        // implicit imports being present.
        attribute(org.gradle.api.attributes.Usage.USAGE_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.Usage::class.java,
        org.gradle.api.attributes.Usage.JAVA_RUNTIME))
        attribute(org.gradle.api.attributes.Category.CATEGORY_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.Category::class.java,
        org.gradle.api.attributes.Category.LIBRARY))
        attribute(org.gradle.api.attributes.LibraryElements.LIBRARY_ELEMENTS_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.LibraryElements::class.java,
        org.gradle.api.attributes.LibraryElements.JAR))
        attribute(org.gradle.api.attributes.Bundling.BUNDLING_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.Bundling::class.java,
        org.gradle.api.attributes.Bundling.EXTERNAL))
    }
}

repositories {
    maven {
        name = "NeoForged"
        url = uri("https://maven.neoforged.net/releases")
    }
    mavenCentral()
}

neoForge {
    version = neoforge_version
    runs {
        register("client") { client() }
        register("server") { server() }
    }
}
dependencies {
    // No explicit slf4j-api here: net.neoforged:neoforge already puts
    // org.slf4j:slf4j-api:{strictly 2.0.9} on the compile classpath through
    // minecraft-dependencies, and a strict constraint cannot be overridden --
    // pinning 2.0.17 made resolution fail outright (run 42842100723).
    compileOnly(project(":pyfm-core"))
    compileOnly(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../loader-adapters/neoforge/src/client/java", "../../../loader-adapters/neoforge/src/compat-26.3/java"))
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(java_version.toInt())
    options.encoding = "UTF-8"
}

// No toolchain block on purpose; see the fabric builds.

tasks.shadowJar {
    configurations = listOf(project.configurations.named("shade").get())
    archiveClassifier.set("all")
    mergeServiceFiles()
    exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA")
    exclude("module-info.class")
}

tasks.jar {
    dependsOn(tasks.shadowJar)
}

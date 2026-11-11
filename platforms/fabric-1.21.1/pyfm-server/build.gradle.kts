plugins {
    id("net.fabricmc.fabric-loom-remap")
    alias(libs.plugins.shadow)
}

val minecraft_version: String = project.property("minecraft_version") as String
val loader_version: String = project.property("loader_version") as String
val fabric_api_version: String = project.property("fabric_api_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pythonforminecraft-server-fabric-1.21.1")
}

// Dependencies that are shaded into the artifact instead of being resolved at
// runtime. Fabric and NeoForge both only load jars that are mods/libraries, so the
// Python runtime has to travel inside the core jar.
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

loom {
    // No split source sets: this build has one side per subproject by design.
}

dependencies {
    minecraft("com.mojang:minecraft:${minecraft_version}")
    mappings(loom.officialMojangMappings())
    modImplementation("net.fabricmc:fabric-loader:${loader_version}")
    modImplementation("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
    compileOnly(libs.slf4j.api)
    // Core classes are provided at runtime by the core jar; compiling
    // against it keeps them out of this artifact, so the jars never duplicate classes.
    compileOnly(project(":pyfm-core"))
    compileOnly(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../loader-adapters/fabric/src/server/java"))
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(java_version.toInt())
    options.encoding = "UTF-8"
}

// No toolchain block on purpose: options.release above pins the bytecode
// level, while the build JVM itself must satisfy the Gradle plugin
// (Loom 1.19 needs JDK 25 even for Minecraft 1.21.1).

tasks.processResources {
    val version = project.version.toString()
    inputs.property("version", version)
    filesMatching("fabric.mod.json") {
        expand("version" to version)
    }
}

tasks.shadowJar {
    configurations = listOf(project.configurations.named("shade").get())
    archiveClassifier.set("all")
    mergeServiceFiles()
    exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA")
    exclude("module-info.class")
}

tasks.remapJar {
    dependsOn(tasks.shadowJar)
    inputFile.set(tasks.shadowJar.get().archiveFile)
}

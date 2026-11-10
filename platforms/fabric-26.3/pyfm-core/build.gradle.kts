plugins {
    id("net.fabricmc.fabric-loom")
    alias(libs.plugins.shadow)
}

val minecraft_version: String = project.property("minecraft_version") as String
val loader_version: String = project.property("loader_version") as String
val fabric_api_version: String = project.property("fabric_api_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pythonforminecraft-core-fabric-26.3")
}

// Dependencies that are shaded into the artifact instead of being resolved at
// runtime. Fabric and NeoForge both only load jars that are mods/libraries, so the
// Python runtime has to travel inside the core jar.
val shade: Configuration = configurations.create("shade")

loom {
    // No split source sets: this build has one side per subproject by design.
}

dependencies {
    minecraft("com.mojang:minecraft:${minecraft_version}")
    implementation("net.fabricmc:fabric-loader:${loader_version}")
    implementation("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
    compileOnly(libs.slf4j.api)
    // GraalPy is shaded into the core jar: Fabric only loads jars in
    // mods/ that are mods themselves, so the Python runtime cannot be a loose library jar.
    implementation(libs.bundles.graalpy)
    "shade"(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../core/src/main/java", "../../../loader-adapters/fabric/src/common/java"))
    }
}

tasks.processResources {
    // The pfm package ships inside the core jar and is unpacked at start-up by
    // PyFmRuntimeResources.
    from("../../../python") {
        include("pfm/**")
        into("pythonforminecraft")
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

// Unobfuscated game: the shadow jar is the artifact, nothing is remapped.
tasks.jar { enabled = false }
tasks.assemble { dependsOn(tasks.shadowJar) }
tasks.build { dependsOn(tasks.shadowJar) }

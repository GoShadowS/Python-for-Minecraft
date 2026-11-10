plugins {
    id("net.fabricmc.fabric-loom-remap")
    alias(libs.plugins.shadow)
}

val minecraft_version: String by project
val loader_version: String by project
val fabric_api_version: String by project
val java_version: String by project

base {
    archivesName.set("pythonforminecraft-core-fabric-1.21.1")
}

// Dependencies that are shaded into the artifact instead of being resolved at
// runtime. Fabric and NeoForge both only load jars that are mods/libraries, so the
// Python runtime has to travel inside the core jar.
val shade: Configuration by configurations.creating

loom {
    // No split source sets: this build has one side per subproject by design.
}

dependencies {
    minecraft("com.mojang:minecraft:${minecraft_version}")
    mappings(loom.officialMojangMappings())
    modImplementation("net.fabricmc:fabric-loader:${loader_version}")
    modImplementation("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
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

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(java_version.toInt()))
    }
}

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

// Example Python mod: a normal Fabric mod jar whose entry point is Python.
plugins {
    id("net.fabricmc.fabric-loom-remap") version "1.19"
}

val minecraft_version: String by project
val loader_version: String by project
val fabric_api_version: String by project
val java_version: String by project

base {
    archivesName.set("pyhello_common-fabric-1.21.1")
}

repositories {
    mavenCentral()
}

dependencies {
    minecraft("com.mojang:minecraft:${minecraft_version}")
    mappings(loom.officialMojangMappings())
    modImplementation("net.fabricmc:fabric-loader:${loader_version}")
    modImplementation("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
    // Compile-only: the language adapter and the core classes come from the
    // installed Python-for-Minecraft jars at runtime.
    compileOnly(files(
    "../../../platforms/fabric-1.21.1/pyfm-core/build/libs/" +
    "pythonforminecraft-core-fabric-1.21.1-1.0.0-all.jar"
    ))
}

// This mod has no Java sources at all.
sourceSets {
    named("main") {
        java.setSrcDirs(emptyList<String>())
    }
}

tasks.processResources {
    from("../python") {
        include("pyhello_common/**")
        into("python")
    }
    from("../python") {
        include("vendor/**")
        into("python")
    }
    val version = project.version.toString()
    inputs.property("version", version)
    filesMatching("fabric.mod.json") {
        expand("version" to version)
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(java_version.toInt())
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(java_version.toInt()))
    }
}

// Example Python mod: a normal Fabric mod jar whose entry point is Python.
plugins {
    id("net.fabricmc.fabric-loom") version "1.19"
}

val minecraft_version: String by project
val loader_version: String by project
val fabric_api_version: String by project
val java_version: String by project

base {
    archivesName.set("pyhello_client-fabric-26.3")
}

repositories {
    mavenCentral()
}

dependencies {
    minecraft("com.mojang:minecraft:${minecraft_version}")
    implementation("net.fabricmc:fabric-loader:${loader_version}")
    implementation("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
    // Compile-only: the language adapter and the core classes come from the
    // installed Python-for-Minecraft jars at runtime.
    compileOnly(files(
    "../../../platforms/fabric-26.3/pyfm-core/build/libs/" +
    "pythonforminecraft-core-fabric-26.3-1.0.0-all.jar"
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
        include("pyhello_client/**")
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

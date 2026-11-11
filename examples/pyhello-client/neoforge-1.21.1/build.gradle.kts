// Example Python mod: a normal NeoForge mod jar whose modLoader is
// "pythonforminecraft", so it contains no Java code at all.
plugins {
    id("net.neoforged.moddev") version "2.0.71"
}

val neoforge_version: String = project.property("neoforge_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pyhello_client-neoforge-1.21.1")
}

neoForge {
    version = neoforge_version
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
    filesMatching("META-INF/neoforge.mods.toml") {
        expand("version" to version)
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(java_version.toInt())
}

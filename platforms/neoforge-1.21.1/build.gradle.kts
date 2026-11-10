// Minecraft 1.21.1 on NeoForge. Java 21.
plugins {
    id("net.neoforged.moddev") version "2.0.71" apply false
    alias(libs.plugins.shadow) apply false
}

subprojects {
    group = rootProject.group.toString()
    version = rootProject.version.toString()
}

// Minecraft 1.21.1 on NeoForge. Java 21.
plugins {
    id("net.neoforged.moddev") version "2.0.148" apply false
    alias(libs.plugins.shadow) apply false
}

subprojects {
    group = rootProject.group.toString()
    version = rootProject.version.toString()
}

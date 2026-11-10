// Minecraft 26.3 on NeoForge. Java 25.
plugins {
    id("net.neoforged.moddev") version "2.0.148" apply false
    alias(libs.plugins.shadow) apply false
}

subprojects {
    group = rootProject.group.toString()
    version = rootProject.version.toString()
}

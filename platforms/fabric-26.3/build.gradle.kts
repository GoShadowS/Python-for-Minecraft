// Minecraft 26.3 on Fabric. Java 25.
// The game is unobfuscated, so no mappings line and no remapping.
plugins {
    id("net.fabricmc.fabric-loom") version "1.20.0-alpha.27" apply false
    alias(libs.plugins.shadow) apply false
}

subprojects {
    group = rootProject.group.toString()
    version = rootProject.version.toString()
}

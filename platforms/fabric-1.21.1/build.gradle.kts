// Minecraft 1.21.1 on Fabric. Java 21.
// Mojang mappings + remapping.
plugins {
    id("net.fabricmc.fabric-loom-remap") version "1.19-SNAPSHOT" apply false
    alias(libs.plugins.shadow) apply false
}

subprojects {
    group = rootProject.group.toString()
    version = rootProject.version.toString()
}

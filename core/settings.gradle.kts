// Standalone build of the loader-agnostic core, so its unit tests can run without a
// Minecraft toolchain. The platform builds compile the same sources directly.
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    versionCatalogs {
        create("libs") { from(files("../gradle/libs.versions.toml")) }
    }
}

rootProject.name = "pythonforminecraft-core"

plugins {
    id("net.neoforged.moddev")
    alias(libs.plugins.shadow)
}

val neoforge_version: String by project
val java_version: String by project

base {
    archivesName.set("pythonforminecraft-server-neoforge-1.21.1")
}

// See the fabric builds: shaded dependencies travel inside the core jar.
val shade: Configuration by configurations.creating

repositories {
    maven {
        name = "NeoForged"
        url = uri("https://maven.neoforged.net/releases")
    }
    mavenCentral()
}

neoForge {
    version.set(neoforge_version)
    runs {
        register("client") { client() }
        register("server") { server() }
    }
}
dependencies {
    compileOnly(libs.slf4j.api)
    compileOnly(project(":pyfm-core"))
    compileOnly(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../loader-adapters/neoforge/src/server/java"))
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

tasks.shadowJar {
    configurations = listOf(project.configurations.named("shade").get())
    archiveClassifier.set("all")
    mergeServiceFiles()
    exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA")
    exclude("module-info.class")
}

tasks.jar {
    dependsOn(tasks.shadowJar)
}

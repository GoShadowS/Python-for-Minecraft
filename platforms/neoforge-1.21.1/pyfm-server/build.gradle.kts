plugins {
    id("net.neoforged.moddev")
    alias(libs.plugins.shadow)
}

val neoforge_version: String = project.property("neoforge_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pythonforminecraft-server-neoforge-1.21.1")
}

// See the fabric builds: shaded dependencies travel inside the core jar.
val shade: Configuration = configurations.create("shade")

repositories {
    maven {
        name = "NeoForged"
        url = uri("https://maven.neoforged.net/releases")
    }
    mavenCentral()
}

neoForge {
    version = neoforge_version
    runs {
        register("client") { client() }
        register("server") { server() }
    }
}
dependencies {
    // No explicit slf4j-api here: net.neoforged:neoforge already puts
    // org.slf4j:slf4j-api:{strictly 2.0.9} on the compile classpath through
    // minecraft-dependencies, and a strict constraint cannot be overridden --
    // pinning 2.0.17 made resolution fail outright (run 42842100723).
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

// No toolchain block on purpose; see the fabric builds.

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

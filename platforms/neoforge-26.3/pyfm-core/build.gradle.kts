plugins {
    `java-library`
    alias(libs.plugins.shadow)
}

val neoforge_version: String by project
val java_version: String by project

base {
    archivesName.set("pythonforminecraft-core-neoforge-26.3")
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

dependencies {
    compileOnly(libs.slf4j.api)
    compileOnly("net.neoforged:neoforge:${neoforge_version}")
    implementation(libs.bundles.graalpy)
    "shade"(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../core/src/main/java", "../../../loader-adapters/neoforge/src/lang/java"))
    }
}

tasks.processResources {
    from("../../../python") {
        include("pfm/**")
        into("pythonforminecraft")
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

tasks.jar {
    manifest {
        // FML loads the Python mod loader from the plugin layer, which requires a LIBRARY
        // jar without a neoforge.mods.toml -- the same shape Kotlin for Forge uses.
        attributes(
        "FMLModType" to "LIBRARY",
        "Implementation-Version" to project.version.toString(),
        )
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

// Fails the build when the shaded jar lost something the Python runtime needs:
// Truffle discovers the Python language through a service file, and the pfm package
// has to be inside the jar so PyFmRuntimeResources can unpack it.
tasks.register("verifyPythonRuntime") {
    val output = tasks.named("shadowJar").flatMap {
        (it as com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar).archiveFile
    }
    inputs.files(output)
    doLast {
        val file = output.get().asFile
        val required = listOf(
        "META-INF/services/com.oracle.truffle.api.TruffleLanguage$Provider",
        "pythonforminecraft/pfm/__init__.py",
        )
        java.util.jar.JarFile(file).use { jar ->
            val missing = required.filter { jar.getJarEntry(it) == null }
            if (missing.isNotEmpty()) {
                throw GradleException("${file.name} is missing required entries: $missing")
            }
        }
        logger.lifecycle("verifyPythonRuntime: {} contains the Truffle service " +
        "registration and the pfm package", file.name)
    }
}

tasks.named("build") { dependsOn("verifyPythonRuntime") }

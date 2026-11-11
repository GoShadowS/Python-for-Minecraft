import java.util.jar.JarFile

plugins {
    `java-library`
    id("net.neoforged.moddev")
    alias(libs.plugins.shadow)
}

val neoforge_version: String = project.property("neoforge_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pythonforminecraft-core-neoforge-26.3")
}

// See the fabric builds: shaded dependencies travel inside the core jar.
// Shadow expands every file in this configuration as a ZIP. Created without
// attributes, Gradle resolves it the legacy way, where the artifact of a
// pom-packaging module is the POM file itself -- that is why shadowJar died on
// "Cannot expand ZIP .../python-community-25.5.5.0.3.pom" on every platform.
// With runtime attributes Gradle matches variants instead, so an aggregator POM
// contributes its dependencies (real jars) and no artifact of its own.
val shade: Configuration = configurations.create("shade") {
    isCanBeConsumed = false
    isCanBeResolved = true
    attributes {
        // Fully qualified on purpose: this must not depend on the Kotlin DSL
        // implicit imports being present.
        attribute(org.gradle.api.attributes.Usage.USAGE_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.Usage::class.java,
        org.gradle.api.attributes.Usage.JAVA_RUNTIME))
        attribute(org.gradle.api.attributes.Category.CATEGORY_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.Category::class.java,
        org.gradle.api.attributes.Category.LIBRARY))
        attribute(org.gradle.api.attributes.LibraryElements.LIBRARY_ELEMENTS_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.LibraryElements::class.java,
        org.gradle.api.attributes.LibraryElements.JAR))
        attribute(org.gradle.api.attributes.Bundling.BUNDLING_ATTRIBUTE,
        objects.named(org.gradle.api.attributes.Bundling::class.java,
        org.gradle.api.attributes.Bundling.EXTERNAL))
    }
}

repositories {
    maven {
        name = "NeoForged"
        url = uri("https://maven.neoforged.net/releases")
    }
    mavenCentral()
}

neoForge {
    version = neoforge_version
}
dependencies {
    // No explicit slf4j-api here: net.neoforged:neoforge already puts
    // org.slf4j:slf4j-api:{strictly 2.0.9} on the compile classpath through
    // minecraft-dependencies, and a strict constraint cannot be overridden --
    // pinning 2.0.17 made resolution fail outright (run 42842100723).
    implementation(libs.bundles.graalpy)
    "shade"(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../core/src/main/java", "../../../loader-adapters/neoforge/src/lang/java", "../../../loader-adapters/neoforge/src/compat-26.3/java"))
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

// No toolchain block on purpose; see the fabric builds.

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
        "META-INF/services/com.oracle.truffle.api.TruffleLanguage\$Provider",
        "pythonforminecraft/pfm/__init__.py",
        )
        JarFile(file).use { jar ->
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

import java.util.jar.JarFile

plugins {
    id("net.fabricmc.fabric-loom-remap")
    alias(libs.plugins.shadow)
}

val minecraft_version: String = project.property("minecraft_version") as String
val loader_version: String = project.property("loader_version") as String
val fabric_api_version: String = project.property("fabric_api_version") as String
val java_version: String = project.property("java_version") as String

base {
    archivesName.set("pythonforminecraft-core-fabric-1.21.1")
}

// Dependencies that are shaded into the artifact instead of being resolved at
// runtime. Fabric and NeoForge both only load jars that are mods/libraries, so the
// Python runtime has to travel inside the core jar.
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

loom {
    // No split source sets: this build has one side per subproject by design.
}

dependencies {
    minecraft("com.mojang:minecraft:${minecraft_version}")
    mappings(loom.officialMojangMappings())
    modImplementation("net.fabricmc:fabric-loader:${loader_version}")
    modImplementation("net.fabricmc.fabric-api:fabric-api:${fabric_api_version}")
    compileOnly(libs.slf4j.api)
    // GraalPy is shaded into the core jar: Fabric only loads jars in
    // mods/ that are mods themselves, so the Python runtime cannot be a loose library jar.
    implementation(libs.bundles.graalpy)
    "shade"(libs.bundles.graalpy)
}

sourceSets {
    named("main") {
        java.setSrcDirs(listOf("../../../core/src/main/java", "../../../loader-adapters/fabric/src/common/java"))
    }
}

tasks.processResources {
    // The pfm package ships inside the core jar and is unpacked at start-up by
    // PyFmRuntimeResources.
    from("../../../python") {
        include("pfm/**")
        into("pythonforminecraft")
    }
}
tasks.withType<JavaCompile>().configureEach {
    options.release.set(java_version.toInt())
    options.encoding = "UTF-8"
}

// No toolchain block on purpose: options.release above pins the bytecode
// level, while the build JVM itself must satisfy the Gradle plugin
// (Loom 1.19 needs JDK 25 even for Minecraft 1.21.1).

tasks.processResources {
    val version = project.version.toString()
    inputs.property("version", version)
    filesMatching("fabric.mod.json") {
        expand("version" to version)
    }
}

// Shadow expands everything it is given as a ZIP, so it gets jars and nothing else.
// Two GraalPy modules -- org.graalvm.python:python-community and
// org.graalvm.python:python -- are POM aggregators: they pull in python-language,
// python-resources, truffle-runtime, truffle-compiler, regex, icu4j and the rest as
// real jars, but Gradle still lists their POM among the resolved artifacts, and
// shadowJar died on "Cannot expand ZIP .../python-community-25.5.5.0.3.pom".
// Filtering here keeps every real GraalPy jar in the mod jar and drops only the POMs.
val shadeArtifacts = project.configurations.named("shade").get()
.incoming.artifactView { lenient(false) }.artifacts

tasks.shadowJar {
    configurations = listOf()
    from(provider {
        shadeArtifacts.artifacts
        .filter { it.file.name.endsWith(".jar") }
        .map { zipTree(it.file) }
    })
    archiveClassifier.set("all")
    mergeServiceFiles()
    exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA")
    exclude("module-info.class")
}

tasks.remapJar {
    dependsOn(tasks.shadowJar)
    inputFile.set(tasks.shadowJar.get().archiveFile)
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
            val names = jar.entries().asSequence().map { it.name }.toList()
            val missing = required.filter { it !in names }
            if (missing.isNotEmpty()) {
                val services = names.filter { it.startsWith("META-INF/services/") }.sorted()
                throw GradleException(
                "${file.name} is missing required entries: $missing" +
                "\n  total entries: " + names.size +
                "\n  com/oracle/truffle entries: " + names.count { it.startsWith("com/oracle/truffle/") } +
                "\n  com/oracle/graal entries: " + names.count { it.startsWith("com/oracle/graal/") } +
                "\n  META-INF/services entries (" + services.size + "):\n    " +
                services.joinToString("\n    ")
                )
            }
        }
        logger.lifecycle("verifyPythonRuntime: {} contains the Truffle service " +
        "registration and the pfm package", file.name)
    }
}

tasks.named("build") { dependsOn("verifyPythonRuntime") }

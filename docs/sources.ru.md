# Использованные первоисточники

Всё ниже прочитано **2026-11-10** из самого проекта-первоисточника (GitHub API / содержимое
репозитория) или из документации самих проектов. Там, где факт нельзя было прочитать из
первоисточника в этой песочнице, стоит пометка `[НЕ ПРОВЕРЕНО ЗДЕСЬ]`.

## Версии Minecraft

| Факт | Источник |
|---|---|
| 26.3 «Wilderness Bound» выпущена 2026-09-15, календарная нумерация (26.1 = первый релиз 2026 года), требуется Java **25**, протокол 777 | https://minecraft.wiki/w/Java_Edition_26.3_Snapshot_3 (инфобокс: «Minimum Java version: Java SE 25»), https://mcreference.com/minecraft-versions/26.3 |
| Ветка 1.21.x работает на Java 21; 1.21.11 была последней версией с префиксом `1.` | https://1up-servers.com/en/blog/minecraft-version-numbers-explained/ |
| 26.x поставляется **деобфусцированной** (клиентский jar 26.3: 10 737 настоящих классов `net/minecraft/`, 0 обфусцированных; 1.21.11: 33 настоящих / 10 201 обфусцированный) | https://github.com/lhns/mc-dependency-provider/pull/35 (исследование выше по потоку, цитируемые числа) |

## Fabric

| Факт | Источник |
|---|---|
| Шаблон 1.21.1: `loader_version=0.20.1`, `loom_version=1.19-SNAPSHOT`, плагин `net.fabricmc.fabric-loom-remap`, `mappings loom.officialMojangMappings()`, `modImplementation`, Java 21, `fabric_api_version=0.116.17+1.21.1` | `FabricMC/fabric-example-mod@1.21.1`: `gradle.properties`, `build.gradle` |
| Шаблон 26.3: тот же loader/loom, плагин **`net.fabricmc.fabric-loom`** (без ремаппинга), **без `mappings`**, `implementation`, Java 25, `fabric_api_version=0.165.2+26.3` | `FabricMC/fabric-example-mod@26.3`: `gradle.properties`, `build.gradle` |
| Интерфейс `LanguageAdapter`: `<T> T create(ModContainer mod, String value, Class<T> type) throws LanguageAdapterException`; адаптеры объявляются в `fabric.mod.json` → `languageAdapters`; объявляющему классу нужен публичный конструктор без аргументов | `FabricMC/fabric-loader@0.20.1`: `src/main/java/net/fabricmc/loader/api/LanguageAdapter.java` |
| Интерфейсы точек входа `ModInitializer#onInitialize` (`main`), `ClientModInitializer#onInitializeClient` (`client`), `DedicatedServerModInitializer#onInitializeServer` (`server`), все `@FunctionalInterface` | `FabricMC/fabric-loader@0.20.1`: `src/main/java/net/fabricmc/api/*.java` |
| Паттерн использования FLK: `{"adapter":"kotlin","value":"mymod.MyMod"}`, `schemaVersion` обязан быть 1, `depends.fabric-language-kotlin`; FLK — это jar мода, который упаковывает библиотеки и объявляет адаптер | https://github.com/FabricMC/fabric-language-kotlin (README), последний релиз `1.14.2+kotlin.2.4.21` (2026-10-09) |
| Loom 1.19 — выпущенная версия (2026-10-23) | GitHub API `repos/FabricMC/fabric-loom/releases` |
| Релизы Fabric Loader: 0.19.5 (2026-08-28), 0.20.0 (2026-10-15), 0.20.1 (2026-10-19) | GitHub API `repos/FabricMC/fabric-loader/releases` |

## NeoForge / FancyModLoader

| Факт | Источник |
|---|---|
| `IModLanguageLoader`: `name()`, `version()`, `loadMod(IModInfo, ModFileScanData, ModuleLayer)`, `default validate(IModFile, Collection<ModContainer>, IIssueReporting)`; «Loaded as a ServiceLoader, from the plugin layer. Jars in the mods directory must have an `FMLModType` of `LIBRARY`»; «Version data is read from the manifest's implementation version» | `neoforged/FancyModLoader@1.21.1` и `@11.x`: `loader/src/main/java/net/neoforged/neoforgespi/language/IModLanguageLoader.java` (байт-в-байт одинаков на обеих ветках) |
| `ModContainer`: `public ModContainer(IModInfo)`, `protected void constructMod()`, `public abstract IEventBus getEventBus()` | `neoforged/FancyModLoader@1.21.1` и `@11.x`: `loader/src/main/java/net/neoforged/fml/ModContainer.java` (идентично) |
| `IModInfo#getModProperties()` существует; FML разбирает в него `[modproperties.<modId>]` | `neoforged/FancyModLoader@1.21.1`: `IModInfo.java`, `moddiscovery/ModInfo.java`, строка 107 |
| Ключи верхнего уровня `neoforge.mods.toml`, разбираемые FML: `modLoader`, `loaderVersion`, `license`, `showAsResourcePack`, `showAsDataPack`, `services`, `properties`, `issueTrackerURL`; ключи мода: `modId`, `namespace`, `version`, `displayName`, `description`, `logoFile`, `logoBlur`, `updateJSONURL`, `modUrl`, `modproperties`. **Ни `clientOnly`/`serverOnly`, ни `entryPoint`.** | `neoforged/FancyModLoader@1.21.1` / `@11.x`: `moddiscovery/ModFileInfo.java`, `moddiscovery/ModInfo.java` |
| KFF — референс: `modLoader="kotlinforforge"`, `loaderVersion="[5,)"`; поставляет jar `kfflang` с `FMLModType: LIBRARY` + `META-INF/services/net.neoforged.neoforgespi.language.IModLanguageLoader`, `kfflib` с `FMLModType: GAMELIBRARY`, `kffmod` как мод; `KotlinLanguageLoader` реализует SPI; `KotlinModContainer extends ModContainer` | `thedarkcolour/KotlinForForge@6.x`: `README.md`, `build.gradle.kts`, `src/kfflang/kotlin/.../KotlinLanguageLoader.kt`, `KotlinModContainer.kt`, `src/kffmod/templates/META-INF/neoforge.mods.toml` |
| KFF 6.x нацелен на MC 1.21.9+ (`min_mc_version=1.21.9`, `unsupported_mc_version=26.4`), toolchain Java 25, версия 6.5.0 | `thedarkcolour/KotlinForForge@6.x`: `gradle.properties`, `build.gradle.kts` |
| Ветки NeoForge: `21.1.x` для MC 1.21.1 (Java 21), `26.3.0.x` для MC 26.3 (Java 25); теги git NeoForge `26.3.0`, `26.3.0-stable` | GitHub API `repos/neoforged/NeoForge/tags`; https://space-node.net/blog/neoforge-download-install-guide-2026 (последняя сборка 1.21.1 — 21.1.265, 26.3 — 26.3.0.100) |
| ModDevGradle — текущий плагин Gradle для NeoForge (`net.neoforged.moddevgradle`), ветка `2.0`; KFF импортирует `net.neoforged.moddevgradle.tasks.JarJar` | `thedarkcolour/KotlinForForge@6.x`: `build.gradle.kts`; GitHub API `repos/neoforged/ModDevGradle/tags` |

## GraalPy

| Факт | Источник |
|---|---|
| Последний релиз `graal-25.5.5` «GraalPy3.13 25.5.5», 2026-11-03 | GitHub API `repos/oracle/graalpython/releases` |
| «GraalPy is a high-performance implementation of the Python language for the JVM … Python 3.13 compliant runtime … first-class support for embedding in Java» | https://github.com/oracle/graalpython |
| Артефакты для встраивания: `org.graalvm.polyglot:polyglot`, `org.graalvm.polyglot:python-community` (Community) / `:python` (Oracle GraalVM), `org.graalvm.python:python-embedding` (помощник под UPL, `GraalPyResources.contextBuilder()`) | https://graalpy.org/jvm-developers/docs/ ; https://central.sonatype.com/artifact/org.graalvm.python/python-embedding |
| Доступ к Java из Python: `import java; java.type("java.math.BigInteger")`, `from java.util import ArrayList`; внешние объекты предстают подклассами `polyglot.ForeignObject` | `oracle/graalpython`: `docs/user/Interoperability.md` |
| Лицензия репозитория: `LICENSE.txt` = «Universal Permissive License (UPL) v. 1.0», «Copyright (c) 2018, 2026, Oracle and/or its affiliates»; также существует `THIRD_PARTY_LICENSE.txt` | GitHub API `repos/oracle/graalpython/contents/LICENSE.txt` |
| `[НЕ ПРОВЕРЕНО ЗДЕСЬ]` тексты лицензий внутри опубликованных артефактов Maven и их точные размеры | Maven Central из этой песочницы недоступен |

## Отвергнутые альтернативы

| Вариант | Изученный источник | Причина |
|---|---|---|
| Chicory (`com.dylibso.chicory`, последний 1.7.5, 2026-03-24), исполняющий CPython, скомпилированный в WASM | GitHub API `repos/dylibso/chicory/releases` | чистая JVM, но Python не видит объекты Java без рукописного моста хоста |
| Jython | состояние проекта | только Python 2.7, не поддерживается |
| CPython через JNI (в стиле Jep) | — | нативная нагрузка под каждую ОС, ломает распространение одним артефактом |

## Факты об этой песочнице (ограничения на проверку)

| Проверка | Результат |
|---|---|
| `java` / `javac` | не установлены (`command not found`) |
| `gradle` | не установлен |
| `apt-get update` | падает: `/var/lib/apt/lists/partial … Permission denied` — JDK установить нельзя |
| `repo1.maven.org`, `maven.fabricmc.net`, `piston-meta.mojang.com` | TLS-соединение отклонено (список разрешённых направлений) |
| `api.github.com`, `pypi.org` | доступны (200) |
| Python для запуска Python-слоя | `Python 3.11.2` |

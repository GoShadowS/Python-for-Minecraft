# Python-for-Minecraft — архитектура и выбор рантайма

Статус: **проектная запись**. Каждый номер версии и каждая сигнатура API ниже прочитаны из
первоисточника 2026-11-10; точные URL — в [`sources.ru.md`](sources.ru.md). Пункты, которые
**не** удалось проверить внутри этой среды разработки, помечены `[НЕ ПРОВЕРЕНО ЗДЕСЬ]` и
повторены в [`testing.ru.md`](testing.ru.md).

---

## 1. Цель и рамки

Python-for-Minecraft — **провайдер языка** для модов Minecraft: аналог
[Fabric Language Kotlin](https://github.com/FabricMC/fabric-language-kotlin) (FLK) и
[Kotlin for Forge](https://github.com/thedarkcolour/KotlinForForge) (KFF) со стороны JVM, но
для Python.

*Python-мод* — это обычный JAR мода для Minecraft: свой id мода, свои метаданные загрузчика,
свои ресурсы, — который зависит от Python-for-Minecraft и чьи точки входа являются объектами
Python. Python-for-Minecraft — не бот, не мост RCON, не отдельная игра и не внутриигровая
консоль: код Python выполняется **внутри JVM игры**, на той стороне (клиент / выделенный
сервер), где мод его объявил.

Вне рамок (намеренно): собственная реализация поверхности Minecraft API. Код Python достигает
игры через Java-взаимодействие; что предоставляет Java/Minecraft/loader API, то Python и может
достать.

---

## 2. Целевая матрица — проверенные факты

| Комбинация | Minecraft | Java | Загрузчик | Метаданные загрузчика | Инструментарий разработки |
|---|---|---|---|---|---|
| Fabric + 1.21.1 | 1.21.1 | 21 | Fabric Loader `0.20.1` | `fabric.mod.json` (схема 1) | Loom `1.19`, id плагина `net.fabricmc.fabric-loom-remap`, `mappings loom.officialMojangMappings()`, `modImplementation`, Fabric API `0.116.17+1.21.1` |
| NeoForge + 1.21.1 | 1.21.1 | 21 | NeoForge `21.1.x` (последняя сборка ветки `21.1.265`) | `META-INF/neoforge.mods.toml` | ModDevGradle `2.0.x` |
| Fabric + 26.3 | 26.3 | **25** | Fabric Loader `0.20.1` | `fabric.mod.json` (схема 1) | Loom `1.19`, id плагина **`net.fabricmc.fabric-loom`** (без ремаппинга), **без строки `mappings`**, **`implementation` вместо `modImplementation`**, `jar` вместо `remapJar`, Fabric API `0.165.2+26.3` |
| NeoForge + 26.3 | 26.3 | **25** | NeoForge `26.3.0.x` (теги `26.3.0`, `26.3.0-stable`) | `META-INF/neoforge.mods.toml` | ModDevGradle `2.0.x` |

Факты, определившие дизайн:

1. **Minecraft 26.x поставляется деобфусцированным.** Клиентский jar 26.3 содержит настоящие
   имена `net/minecraft/...` и ни одного обфусцированного, Mojang не публикует
   `client_mappings` для этой ветки, а у Fabric нет сборок Yarn для 26.x. Следствие: для 26.x
   Fabric использует *не-ремаппящий* плагин Loom, обычные зависимости `implementation` и `jar`;
   сборка Fabric 1.21.1 продолжает использовать ремаппящий плагин и маппинги Mojang.
   **Следовательно, одна конфигурация Gradle не может обслуживать обе версии Fabric**, и
   артефакты не взаимозаменяемы.
2. **Java различается по веткам**: 21 для 1.21.1, 25 для 26.x. Четыре сборки используют
   отдельные Gradle toolchain'ы и являются отдельными сборками Gradle, а не одной.
3. **Fabric находит точки входа декларативно** (`fabric.mod.json` → `entrypoints`), а
   *языковой адаптер* (`net.fabricmc.loader.api.LanguageAdapter`,
   `<T> T create(ModContainer, String, Class<T>)`, регистрируемый через `languageAdapters`)
   решает, как строка `value` становится объектом. Именно так работает FLK
   (`{"adapter": "kotlin", "value": "mymod.MyMod"}`).
4. **У NeoForge нет аналога адаптеров из `fabric.mod.json`**; у него есть *SPI загрузчика
   модов*: `net.neoforged.neoforgespi.language.IModLanguageLoader`
   (`name()`, `version()`, `loadMod(IModInfo, ModFileScanData, ModuleLayer)`,
   `validate(IModFile, Collection<ModContainer>, IIssueReporting)`), обнаруживаемый через
   `ServiceLoader` **из слоя плагинов** и выбираемый для каждого файла мода парой
   `modLoader="…"` + `loaderVersion="[…)"` в `neoforge.mods.toml`. Jar, предоставляющий его,
   обязан нести атрибут манифеста `FMLModType: LIBRARY`. KFF делает ровно это
   (`modLoader="kotlinforforge"`). Исходники SPI **идентичны** на ветках `1.21.1` и `11.x`
   (26.x) репозитория `neoforged/FancyModLoader`, поэтому одна реализация обслуживает обе
   ветки NeoForge.
5. В `neoforge.mods.toml` нет ключа `entryPoint`. Пользовательские данные мода читаются из
   `[modproperties.<modId>]`, которые FML разбирает в `IModInfo#getModProperties()`.
   В парсере FML нет флага файла мода `clientOnly`/`serverOnly` — разделение по сторонам на
   NeoForge делается отдельными jar плюс защитами `Dist`.

---

## 3. Рантайм Python: рассмотренные варианты

| Вариант | Python | Внутри JVM | Java-взаимодействие | Кроссплатформенный единый артефакт | Вердикт |
|---|---|---|---|---|---|
| **GraalPy** (`org.graalvm.polyglot:python-community`, 25.5.5, 2026-11-03) | **3.13** | да, чистая JVM | первоклассное: `import java; java.type("…")`, объекты хоста передаются как bindings | да (jar'ы, нативный код не требуется) | **выбран** |
| Chicory + CPython-WASM (`com.dylibso.chicory`, 1.7.5) | 3.11/3.13 CPython | да, чистая JVM | плохое: Python видит WASI, а не объекты Java; каждый вызов требует рукописного моста хоста | да | отвергнут: Java-взаимодействие — ключевое требование |
| Jython | только 2.7 | да | хорошее | да | отвергнут: Python 2, не поддерживается |
| CPython + JNI (Jep, py4j-embeddings) | 3.x | частично | хорошее | **нет** — нативные сборки под каждую ОС | отвергнут: ломает распространение одним артефактом |
| Отдельный процесс Python / сокет / мост RCON | любой | **нет** | н/д | н/д | отвергнут заданием: нужен провайдер языка внутри JVM |

Почему GraalPy:

* современный Python 3.13 (релиз `graal-25.5.5`, «GraalPy3.13», опубликован 2026-11-03);
* спроектирован для встраивания: `org.graalvm.polyglot.Context`,
  `GraalPyResources.contextBuilder()`, задокументированные координаты Maven/Gradle на Maven
  Central;
* настоящее двустороннее взаимодействие — Python вызывает Java через модуль `java`
  (`java.type("java.math.BigInteger")`, `from java.util import ArrayList`), Java вызывает
  Python через `Value`;
* чистая JVM: одни и те же jar'ы работают на Windows, macOS и Linux, на клиенте и на
  выделенном сервере, без нативной нагрузки под каждую платформу;
* совместимая с pip модель пакетов, на которой строится упаковка зависимостей из
  [`dependencies.ru.md`](dependencies.ru.md);
* лицензия: репозиторий `oracle/graalpython` содержит `LICENSE.txt` = **UPL v1.0**
  (пермиссивная). `[НЕ ПРОВЕРЕНО ЗДЕСЬ]` тексты лицензий *внутри* опубликованных артефактов
  Maven скачать в этой среде не удалось (Maven Central недоступен); сборка копирует все
  найденные в затенённых jar файлы лицензий в `META-INF/licenses/`, а
  `THIRD_PARTY_LICENSES.md` перечисляет, что нужно сохранить.

Издержки, честно:

* **Размер.** Затенённый рантайм GraalPy велик (jar языка, Truffle, данные ICU). Точный размер
  в байтах здесь измерить не удалось — Maven Central в этой песочнице недоступен.
  `[НЕ ПРОВЕРЕНО ЗДЕСЬ]`
* **Старт/память.** Создание контекста стоит времени и кучи; мы создаём по одному контексту на
  Python-мод (см. §6) и запускаем их лениво.
* **Производительность.** На обычном OpenJDK Truffle исполняет Python в интерпретаторе (без
  runtime-компилятора), поэтому `engine.WarnInterpreterOnly` заглушён намеренно. Код
  Python-модов нельзя писать под горячие циклы на каждый кадр.
* **Нативные расширения Python** (C-модули вроде бинарников numpy) вне рамок; поддерживаются
  только чисто Python'овые wheel.

---

## 4. Модель компонентов (клиент против серверного компонента)

Три артефакта на пару (загрузчик × Minecraft). Они никогда не делят классы, поэтому установка
более чем одного не может дать дублирующиеся классы в загрузчике классов.

| Артефакт | Id мода | Fabric `environment` / тип NeoForge | Содержимое | Нужен, когда |
|---|---|---|---|---|
| `pythonforminecraft-core-<loader>-<mc>-<v>.jar` | `pythonforminecraft_core` (мод Fabric **без** точек входа) / jar с `FMLModType: LIBRARY` (NeoForge, слой плагинов) | `*` / LIBRARY | независимое от загрузчика ядро + затенённый GraalPy + Python-пакет `pfm` + языковой адаптер (Fabric) / service `IModLanguageLoader` (NeoForge). **Клиентских классов нет.** | всегда |
| `pythonforminecraft-client-<loader>-<mc>-<v>.jar` | `pythonforminecraft` | `client` / мод NeoForge с защитами `Dist` | клиентская инициализация: клиентские точки входа, клиентские события, клиентские хендлы | инстанс — клиент |
| `pythonforminecraft-server-<loader>-<mc>-<v>.jar` | `pythonforminecraft_server` | `*` / мод NeoForge | общая инициализация + инициализация выделенного сервера: общие/серверные точки входа, серверные события, серверные хендлы, регистрация команд | Python-код должен работать на выделенном сервере |

Правила, которые это обеспечивает:

* **клиентскому** Python-моду нужны *ядро + клиент* на клиенте и **ничего** на сервере — jar
  ядра не несёт клиентских классов, а его Fabric-environment равен `*`, так что даже оказавшись
  на сервере он остаётся инертным;
* **серверному** Python-моду нужны *ядро + сервер* на сервере; клиентский jar не требуется и не
  должен там стоять;
* клиентские классы живут только в клиентском артефакте, поэтому выделенный сервер никогда их
  не загружает (Fabric полностью пропускает моды с `environment: client`; на NeoForge
  клиентский jar просто не устанавливается, а всё внутри него защищено `Dist`);
* клиентский артефакт никогда не заявляет, что исполняет Python на сервере. Если установлены
  только *ядро + клиент*, Python работает лишь на клиенте.

Почему три, а не два: разделение на два артефакта либо дублировало бы классы ядра между
клиентским и серверным jar (тот самый отказ, который задание запрещает), либо заставило бы
классы одного jar зависеть от jar, намеренно отсутствующего на одной из сторон.

---

## 5. Формат Python-мода

Python-мод — обычный jar мода. Его собственные метаданные принадлежат загрузчику;
Python-for-Minecraft добавляет одну специфичную для загрузчика часть.

### Fabric (`fabric.mod.json`)

```json
{
  "schemaVersion": 1,
  "id": "pyhello_client",
  "version": "1.0.0",
  "environment": "client",
  "entrypoints": {
    "client": [ { "adapter": "python", "value": "pyhello_client.entry:PyHelloClient" } ]
  },
  "custom": {
    "pythonforminecraft": {
      "python_root": "python",
      "vendor": ["python/vendor"],
      "modules": ["pyhello_client"]
    }
  },
  "depends": {
    "pythonforminecraft_core": ">=1.0.0",
    "pythonforminecraft": ">=1.0.0"
  }
}
```

Адаптер `python` объявляется артефактом ядра в `languageAdapters` точно так же, как FLK
объявляет `kotlin`.

### NeoForge (`META-INF/neoforge.mods.toml`)

```toml
modLoader = "pythonforminecraft"
loaderVersion = "[1,)"
license = "Apache-2.0"

[[mods]]
modId = "pyhello_common"
version = "1.0.0"
displayName = "PyHello Common"

[modproperties.pyhello_common]
python_root = "python"
vendor = ["python/vendor"]
modules = ["pyhello_common"]
pyfm_main = "pyhello_common.entry:PyHelloCommon"
pyfm_server = "pyhello_common.entry:PyHelloCommon"
```

`modLoader` выбирает наш `IModLanguageLoader`; точки входа едут в `[modproperties.<modId>]`,
потому что у FML нет ключа `entryPoint`. **Эта асимметрия между двумя загрузчиками настоящая и
не спрятана за общей абстракцией.**

### Обозначение точки входа (одинаково на обоих загрузчиках)

`"package.module:attribute"` (в стиле console-script):

| Атрибут — это | Поведение |
|---|---|
| вызываемый объект | вызывается без аргументов (или с `pfm.ModContext`, если объявлен один параметр) |
| класс | создаётся экземпляр, затем вызываются его хуки жизненного цикла |
| объект | вызываются его хуки жизненного цикла |

Хуки жизненного цикла: `on_initialize()` (общий), `on_client_initialize()` (клиент),
`on_server_initialize()` (выделенный сервер). События регистрируются декораторами, а не по
имени хука (`@pfm.event("server_start")`).

---

## 6. Рантайм, изоляция, потоки

* **Один `Engine` на сторону, один `Context` на Python-мод.** Отдельные контексты дают каждому
  моду свои `sys.modules`, `sys.path` и реестр `pfm`, поэтому импорты и глобальные переменные
  не могут протекать между модами, а мод можно разобрать в одиночку.
* **Исходники Python распаковываются, а не читаются из jar.** Python-файлы внутри jar мода
  распаковываются в `<игра>/pythonforminecraft/<modId>/python` (кэш по хешу содержимого), и
  этот путь добавляется в начало `sys.path`; завендоренные wheel распаковываются так же. Во
  время игры ничего не скачивается.
* **Однопоточное исполнение с явной блокировкой.** Контекст Truffle не безопасен для
  одновременного доступа, а у Minecraft есть поток клиента и (в одиночной игре) поток
  интегрированного сервера. Каждый вызов Python проходит через `PythonRuntime.enter(...)`,
  который держит реентерабельную блокировку и делает `enter()`/`leave()` контекста в вызывающем
  потоке.
* **Ожидания по потокам задокументированы для каждого события** и проверяются при
  диспетчеризации: серверные события выполняются в потоке сервера, клиентские — в потоке
  клиента.

## 7. Ошибки, завершение, доверие

* Ошибка Python сообщается как: id мода → точка входа/обработчик → файл → строка → трейсбек
  Python. Мод, чья точка входа на Python бросила исключение, **не** сообщается как загруженный:
  адаптер Fabric бросает `LanguageAdapterException`, загрузчик NeoForge — `ModLoadingException`,
  поэтому отказ показывает сам загрузчик.
* Завершение: реестры очищаются, каждый контекст закрывается, engine закрывается. Привязано к
  событиям остановки клиента/сервера Fabric, событию остановки сервера NeoForge и, как запасной
  вариант, к shutdown hook JVM.
* **Это не песочница.** Python-моды получают доступ к хосту, эквивалентный самому процессу JVM
  игры: файловая система, сеть, `System.exit`. Устанавливайте только те Python-моды, которым
  доверяете. См. [`security.ru.md`](security.ru.md).

## 8. Блоккеры

См. [`testing.ru.md`](testing.ru.md). Коротко: в этой песочнице нет JDK, Gradle и маршрута к
Maven Central / Fabric Maven / Mojang, поэтому ни один JVM-артефакт нельзя было
скомпилировать или запустить здесь. Всё JVM-сторона в этом репозитории написана против
сигнатур, прочитанных из первоисточников, и помечена `[НЕ ПРОВЕРЕНО ЗДЕСЬ]` до сборки.

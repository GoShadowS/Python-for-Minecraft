# Написание и сборка Python-мода

Python-мод — это обычный jar мода. У него свой id мода, свои метаданные, своя точка входа и
свой Python-код. От Python-for-Minecraft он зависит так же, как Java-мод зависит от
библиотеки, — через механизм зависимостей загрузчика, а не через плагин сборки.

Это руководство опирается на два примера модов в `examples/` — настоящие проекты с
собственными метаданными и файлами сборки. Читайте их вместе с этой страницей.

## 1. Выберите, что такое ваш мод

| Ваш мод | Установить на клиент | Установить на выделенный сервер |
| --- | --- | --- |
| клиентский (HUD, экраны, клавиши) | `pythonforminecraft_core` + `pythonforminecraft` | ничего |
| общая / серверная логика | `pythonforminecraft_core` + `pythonforminecraft` | `pythonforminecraft_core` + `pythonforminecraft_server` |

Полная матрица — в [`installation.ru.md`](installation.ru.md). Клиентскому Python-моду на
сервере ничего не нужно: в jar ядра нет клиентских классов, а клиентский компонент — это
отдельный jar со своим id мода.

## 2. Структура

```
mymod/
├── fabric-1.21.1/            # по одному проекту Gradle на поддерживаемую комбинацию
│   ├── build.gradle.kts
│   ├── gradle.properties
│   ├── settings.gradle.kts
│   └── src/main/resources/fabric.mod.json
├── neoforge-1.21.1/
│   └── src/main/resources/META-INF/neoforge.mods.toml
└── python/                   # общий для всех комбинаций
    ├── mymod/
    │   ├── __init__.py
    │   └── entry.py
    └── vendor/               # необязательно, создаётся tools/vendor_deps.py
```

Исходники Python общие; различаются только метаданные и сборка. Дублировать Python-код под
каждый загрузчик причин нет.

У Python-мода **нет Java-исходников**. Сборки примеров говорят это явно
(`java.setSrcDirs(emptyList<String>())`); так jar остаётся без случайно скомпилированных
Java-классов.

## 3. Точка входа

`python/mymod/entry.py`:

```python
import pfm

MARKER = "[mymod]"


class MyMod:
    """Создаётся Python-for-Minecraft один раз; экземпляр живёт весь запуск."""

    def on_initialize(self):
        pfm.log.info("%s общая инициализация на стороне %s" % (MARKER, pfm.side()))

    def on_client_initialize(self):
        pfm.log.info("%s клиентская инициализация" % MARKER)

    def on_server_initialize(self):
        pfm.log.info("%s инициализация выделенного сервера" % MARKER)


@pfm.event("player_join")
def on_player_join(event):
    pfm.log.info("%s игрок подключился: %s" % (MARKER, event.data))


@pfm.command("myhello", usage="/myhello", permission=0)
def myhello(ctx):
    ctx.reply("%s привет из Python" % MARKER)
```

На точку входа ссылаются как `package.module:Attribute`, здесь — `mymod.entry:MyMod`.
Атрибутом может быть класс, экземпляр или вызываемый объект; см.
[`api.ru.md`](api.ru.md#1-точки-входа).

### Fabric: `fabric.mod.json`

```json
{
    "schemaVersion": 1,
    "id": "mymod",
    "version": "${version}",
    "name": "My Mod",
    "environment": "*",
    "license": "Apache-2.0",
    "entrypoints": {
        "main": [
            {"adapter": "python", "value": "mymod.entry:MyMod"}
        ],
        "server": [
            {"adapter": "python", "value": "mymod.entry:MyMod"}
        ]
    },
    "custom": {
        "pythonforminecraft": {
            "python_root": "python",
            "modules": ["mymod"],
            "vendor": ["python/vendor"]
        }
    },
    "depends": {
        "pythonforminecraft_core": ">=1.0.0",
        "pythonforminecraft_server": ">=1.0.0",
        "fabricloader": ">=0.20.1",
        "minecraft": "~1.21.1",
        "java": ">=21"
    }
}
```

* `environment` обязан быть `"client"` для клиентского мода. Тогда Fabric никогда не загрузит
  его на выделенном сервере.
* используйте `main` для общего кода, `client` для клиентского, `server` для кода выделенного
  сервера.
* зависьте от `pythonforminecraft` для клиентского мода и от `pythonforminecraft_server` для
  общего/серверного кода. Обоим также нужен `pythonforminecraft_core`.

### NeoForge: `META-INF/neoforge.mods.toml`

```toml
modLoader = "pythonforminecraft"
loaderVersion = "[1,)"
license = "Apache-2.0"

[[mods]]
modId = "mymod"
version = "${version}"
displayName = "My Mod"
description = "A Python mod."

[[dependencies.mymod]]
modId = "neoforge"
type = "required"
versionRange = "[21.1,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.mymod]]
modId = "pythonforminecraft_server"
type = "required"
versionRange = "[1.0.0,)"
ordering = "AFTER"
side = "BOTH"

[modproperties.mymod]
python_root = "python"
modules = ["mymod"]
vendor = ["python/vendor"]
pyfm_main = "mymod.entry:MyMod"
pyfm_server = "mymod.entry:MyMod"
```

У NeoForge **нет** аналога ключа адаптера из `fabric.mod.json` и **нет** ключа `entryPoint`.
Точки входа передаются как свойства мода (`pyfm_main`, `pyfm_client`, `pyfm_server`) и читаются
через `IModInfo#getModProperties()`. Разделение по сторонам делается отдельными jar, потому что
в `neoforge.mods.toml` нет флага `clientOnly`/`serverOnly`. Это различие настоящее, и PyFM его
не прячет.

## 4. Сборка

Каждая комбинация — собственная сборка Gradle, потому что четыре комбинации действительно
разные:

| | Fabric 1.21.1 | Fabric 26.3 | NeoForge 1.21.1 | NeoForge 26.3 |
| --- | --- | --- | --- | --- |
| Плагин Gradle | `net.fabricmc.fabric-loom-remap` | `net.fabricmc.fabric-loom` | `net.neoforged.moddevgradle` | `net.neoforged.moddevgradle` |
| маппинги | `loom.officialMojangMappings()` | нет | н/д | н/д |
| конфигурация зависимостей | `modImplementation` | `implementation` | `neoForge` | `neoForge` |
| JDK | 21 | 25 | 21 | 25 |
| Ветка Gradle | 9.8.2 | 9.8.2 | 8.14.5 | 8.14.5 |

```sh
cd examples/pyhello-common/fabric-1.21.1 && gradle build
```

**Эти сборки ни разу не выполнялись** — в среде, где писался проект, нет JDK и нет доступа к
Maven Central. См. [`testing.ru.md`](testing.ru.md). Сгенерированные файлы сборки лежат в
репозитории, чтобы их можно было запустить, как только появится инструментарий.

`build.gradle.kts` обязан копировать Python-код в jar:

```kotlin
tasks.processResources {
    from("../python") { include("mymod/**"); into("python") }
    from("../python") { include("vendor/**"); into("python") }
    filesMatching("fabric.mod.json") { expand("version" to project.version.toString()) }
}
```

## 5. Сторонние пакеты

См. [`dependencies.ru.md`](dependencies.ru.md). Коротко: зафиксируйте их в `requirements.txt`
с версиями и хешами, выполните `tools/vendor_deps.py`, закоммитьте `python/vendor/`. Во время
игры ничего не скачивается.

## 6. Проверка мода перед публикацией

```sh
python3 tools/validate_metadata.py
```

Эта команда разрешает каждую точку входа против исходников Python, проверяет id мода,
environment, зависимость от правильного компонента PyFM, а также существование объявленных
модулей и каталогов вендоринга. Это самый дешёвый способ поймать опечатку, которая иначе
проявилась бы только в логе падения при старте.

## 7. Необязательных правил нет

* Маркеры в логе: дайте своему моду стабильный префикс (примеры используют
  `[pyhello-common]`), чтобы его вывод можно было вытащить из большого лога grep'ом.
* Не импортируйте модули другого Python-мода. У каждого мода свой рантайм и свой `sys.path`;
  кросс-импорты работают только случайно.
* Не храните ссылки на игровые объекты между перезапусками сервера; `pfm` освобождает рантайм
  при завершении.
* Python-код вашего мода доверенный и не изолирован. Не загружайте недоверенный Python. См.
  [`security.ru.md`](security.ru.md).

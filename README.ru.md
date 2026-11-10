# Python for Minecraft

> Аналог модов **«Kotlin for Forge»** и **«Fabric Language Kotlin»** для модов, написанных на
> Python.
>
> Работает с загрузчиками **NeoForge** и **Fabric**, для **Minecraft 1.21.1** и **26.3**.

[English version](README.md)

Это **провайдер языка**, а не бот-фреймворк и не инструмент для RCON/консоли. Вы пишете
обычный мод для Minecraft, точка входа которого — Python; загрузчик находит его, а
Python-for-Minecraft (PyFM) исполняет его внутри той же JVM, что и игра.

---

## ⚠ Прочитайте это до использования

Репозиторий написан в песочнице, где **нет JDK и нет доступа к Maven Central**. Поэтому:

* **Python**-половина реализована и протестирована — здесь проходят 92 модульных теста;
* **Java**-половина (34 файла) написана, но **ни разу не компилировалась**;
* **ни одна сборка Gradle не выполнялась**, и **ни клиент, ни выделенный сервер ни разу не
  запускались**;
* клиентский мод **спроектирован** так, чтобы не требовать ничего на сервере, и это проверено
  статически, но **в рантайме это не наблюдалось**.

Каждое утверждение в репозитории помечено способом проверки, а каждая заблокированная
проверка записана с точной причиной в [`docs/testing.ru.md`](docs/testing.ru.md). Ничто не
выдано за работающее, если оно не работало.

---

## Что это делает

* Исполняет Python-моды **внутри JVM** через GraalPy 3.13 — без отдельного процесса, без
  сетевого моста, без внешнего сервиса.
* **Отдельный контекст GraalPy на каждый Python-мод**: свои пространства имён, свой
  `sys.path`, падение одного мода не роняет остальные.
* **Три артефакта на загрузчик**: `pythonforminecraft_core` (обе стороны),
  `pythonforminecraft` (клиент), `pythonforminecraft_server` (серверный компонент). Классы
  клиента никогда не загружаются на выделенном сервере.
* **Четыре независимые конфигурации сборки**, потому что Fabric 1.21.1, Fabric 26.3, NeoForge
  1.21.1 и NeoForge 26.3 действительно различаются (разный плагин Loom, маппинги, конфигурация
  зависимостей, JDK и ветка Gradle).
* Python-зависимости **вендорятся на этапе сборки**, фиксируются по хешу и кладутся внутрь jar
  мода. Во время игры ничего не скачивается.
* Ошибки Python сообщаются с **id мода, фазой и `at file:line`**, а упавший мод не помечается
  как загруженный.

## Чего это не делает

PyFM **не** даёт Python «весь Minecraft API». Публичная поверхность: девять событий, три
хендла (`pfm.mc.server` / `.client` / `.player`), команды, логирование и
`pfm.java.import_class(...)` для прямого Java-взаимодействия. Нет API реестров, блоков,
предметов, экранов, сущностей и датапаков, нет миксинов, нет сети, нет горячей перезагрузки и
**нет песочницы** — Python-моды это доверенный код с тем же доступом, что и у JVM, в которой
они работают.

Подробности: [`docs/comparison.ru.md`](docs/comparison.ru.md) (сравнение с Kotlin for Forge и
Fabric Language Kotlin по функциям) и [`docs/api.ru.md`](docs/api.ru.md).

## Python-мод выглядит так

```python
import pfm


class MyMod:
    def on_initialize(self):
        pfm.log.info("привет из Python на стороне %s" % pfm.side())


@pfm.event("player_join")
def on_player_join(event):
    pfm.log.info("игрок подключился: %s" % event.data)


@pfm.command("myhello", usage="/myhello")
def myhello(ctx):
    ctx.reply("привет из Python")
```

а загрузчик находит его через обычные метаданные мода — Fabric:

```json
"entrypoints": {
    "main": [{"adapter": "python", "value": "mymod.entry:MyMod"}]
}
```

NeoForge:

```toml
modLoader = "pythonforminecraft"
[modproperties.mymod]
pyfm_main = "mymod.entry:MyMod"
```

## Карта репозитория

| Путь | Содержимое |
| --- | --- |
| `python/pfm/` | публичный Python-пакет (`pfm`) — точки входа, события, команды, логирование, interop |
| `python/tests/` | 92 модульных теста Python-стороны с подставным мостом |
| `core/` | независимое от загрузчика Java-ядро (21 файл): рантайм, изоляция, протокол, трейсбеки, ресурсы |
| `loader-adapters/fabric/` | языковой адаптер Fabric, клиентские и серверные хуки, команды |
| `loader-adapters/neoforge/` | `IModLanguageLoader` NeoForge, контейнер мода, клиентские и серверные хуки, команды |
| `platforms/<loader>-<mc>/` | сгенерированные сборки Gradle, по три подпроекта |
| `examples/pyhello-client/`, `examples/pyhello-common/` | два настоящих тестовых Python-мода для всех четырёх комбинаций |
| `tools/` | `vendor_deps.py`, `validate_metadata.py`, `check_java.py`, `gen_builds.py`, `gen_examples.py` |
| `docs/` | архитектура, API, авторство, установка, зависимости, безопасность, тестирование, сравнение |

## Документация

| Документ | Русский | English |
| --- | --- | --- |
| Архитектура и выбор рантайма | [docs/architecture.ru.md](docs/architecture.ru.md) | [docs/architecture.md](docs/architecture.md) |
| Публичный API, точки входа, события | [docs/api.ru.md](docs/api.ru.md) | [docs/api.md](docs/api.md) |
| Написание и сборка Python-мода | [docs/authoring.ru.md](docs/authoring.ru.md) | [docs/authoring.md](docs/authoring.md) |
| Матрица загрузчик/версия/сторона, установка | [docs/installation.ru.md](docs/installation.ru.md) | [docs/installation.md](docs/installation.md) |
| Упаковка Python-зависимостей | [docs/dependencies.ru.md](docs/dependencies.ru.md) | [docs/dependencies.md](docs/dependencies.md) |
| Доверие, безопасность, полномочия | [docs/security.ru.md](docs/security.ru.md) | [docs/security.md](docs/security.md) |
| Отчёт о тестировании | [docs/testing.ru.md](docs/testing.ru.md) | [docs/testing.md](docs/testing.md) |
| Сравнение с референсными проектами | [docs/comparison.ru.md](docs/comparison.ru.md) | [docs/comparison.md](docs/comparison.md) |
| Устранение неполадок и ограничения | [docs/troubleshooting.ru.md](docs/troubleshooting.ru.md) | [docs/troubleshooting.md](docs/troubleshooting.md) |
| Первоисточники | [docs/sources.ru.md](docs/sources.ru.md) | [docs/sources.md](docs/sources.md) |

## Как проверить самому

Проверки, не требующие JDK, работают где угодно:

```sh
cd python && python3 -m unittest discover -s tests -t .   # Ran 92 tests ... OK
python3 tools/validate_metadata.py                        # PASSED: 30 checks
python3 tools/validate_metadata.py --self-test            # SELF-TEST PASSED: 4/4
python3 tools/check_java.py                               # PASSED: 34 files / 33 types
python3 tools/vendor_deps.py --check \
  --requirements examples/pyhello-common/requirements.txt \
  --out examples/pyhello-common/python/vendor             # ok: six 1.17.0
```

Всё остальное — сборки Gradle, осмотр jar, запуски, проверка маркеров в логе — требует JDK 21
**и** 25 плюс доступ к моддинг-maven'ам и к Mojang. `./build-all.sh` выполняет всё это, а в
`.github/workflows/ci.yml` есть матрица из четырёх комбинаций. Ни то, ни другое этим проектом
не выполнялось.

## Лицензия

Apache-2.0 — см. [`LICENSE`](LICENSE) и [`NOTICE`](NOTICE). Сторонние лицензии, включая
GraalPy и Truffle (UPL 1.0), перечислены в
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) с указанием способа установления каждой.

В `NOTICE` сейчас указан коллективный правообладатель, потому что владелец репозитория не
назвал юридическое имя; перед любым релизом эту строку нужно исправить.

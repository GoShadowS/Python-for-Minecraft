# Устранение неполадок и ограничения

Формат каждой диагностики здесь взят из кода этого репозитория. Там, где симптом нельзя было
воспроизвести, потому что ничего не запускалось, это сказано прямо, а не придумано.

## 1. Чтение лога

Весь вывод Python-for-Minecraft имеет префикс `[PyFM]`. Сначала ищите его:

```sh
grep '\[PyFM\]' logs/latest.log
```

Падающий Python-мод даёт:

```
[PyFM] Python mod 'pyhello_common' failed during server_initialize
  at python/pyhello_common/entry.py:27
  Traceback (most recent call last):
    File "python/pyhello_common/entry.py", line 27, in on_server_initialize
      raise RuntimeError("boom")
  RuntimeError: boom
```

Id мода, фаза и кадр `at file:line` присутствуют всегда. Исключение хоста (Java) вместо этого
заканчивается строкой `host exception: <класс>: <сообщение>`.

## 2. Симптомы

| Симптом | Вероятная причина | Что делать |
| --- | --- | --- |
| Загрузчик сообщает об отсутствии обязательного мода: `pythonforminecraft_core` | jar ядра нет в `mods/`, либо это jar для другой комбинации загрузчик/Minecraft | установите jar ядра, соответствующий вашему загрузчику **и** версии; артефакты не взаимозаменяемы |
| Мод с `environment: client` отсутствует на выделенном сервере | так и задумано | клиентский Python-мод не должен стоять на сервере. Ничего не сломано |
| `modLoader "pythonforminecraft" not found` (NeoForge) | нет jar ядра, либо в нём нет `FMLModType: LIBRARY` | переустановите jar ядра; `unzip -p <core.jar> META-INF/MANIFEST.MF` должен показывать `FMLModType: LIBRARY` |
| `No language adapter named 'python'` (Fabric) | нет jar ядра, либо в нём не объявлен `languageAdapters.python` | переустановите jar ядра; проверьте `fabric.mod.json` внутри него |
| Ошибка точки входа с упоминанием `package.module:Attribute` | опечатка, либо модуля нет внутри jar, либо атрибута не существует | выполните `python3 tools/validate_metadata.py`; затем `unzip -l <вашмод.jar> \| grep python/`, чтобы убедиться, что код действительно упакован |
| `no current Python mod; pfm.event()/pfm.command() can only be used while Python-for-Minecraft is initialising a mod` | `pfm.event`/`pfm.command` использованы во время импорта вне рантайма мода, либо из хелпера, импортируемого двумя модами | украшайте только при импорте модуля внутри собственного пакета, либо передавайте `mod_id` явно |
| `ModuleNotFoundError` для завендоренного пакета | `python/vendor` не скопирован в jar, либо метаданные его не объявляют | проверьте `custom.pythonforminecraft.vendor` (Fabric) / `vendor` в `[modproperties]` (NeoForge) и что `processResources` копирует `vendor/**` |
| `ImportError` внутри пакета с компилируемым расширением | не поддерживается вовсе | см. [`dependencies.ru.md`](dependencies.ru.md) §4. Только чисто Python'овые wheel |
| Вывод `print()` из Python пропадает | stdout направляется в лог игры через `PyFmLogStream` | ищите текст без префикса `[PyFM]`; лучше используйте `pfm.log` |
| Устаревший Python-код после обновления | распакованные исходники кэшируются файлом-маркером | удалите `<игра>/pythonforminecraft/<modId>/` (маркер `.pyfm-extracted`) и `<игра>/pythonforminecraft/runtime/` (маркер `.pyfm-runtime`); они будут созданы заново |
| `verifyPythonRuntime` роняет сборку ядра | затенённый jar потерял service-регистрацию Truffle или пакет `pfm` | проверьте, что `mergeServiceFiles()` по-прежнему применяется и что `processResources` копирует `python/pfm/**` в `pythonforminecraft/` |
| Python-код очень медленный | GraalPy без компилятора GraalVM откатывается к интерпретатору | ожидаемо на обычной JVM. `engine.WarnInterpreterOnly` PyFM глушит, так что предупреждения не будет — только разница в скорости |
| `python.allowAllAccess=false` ломает мод | доступ к хосту отозван, поэтому взаимодействие перестаёт работать | этот режим не проверен; см. [`security.ru.md`](security.ru.md) §3 |

## 3. Файлы, которые PyFM создаёт в рантайме

| Путь (относительно каталога игры) | Назначение | Маркер |
| --- | --- | --- |
| `config/pythonforminecraft.properties` | необязательная конфигурация | — |
| `pythonforminecraft/<modId>/<хеш>/` | исходники Python этого мода, распакованные из его jar | `.pyfm-extracted` |
| `pythonforminecraft/runtime/<версия>/` | пакет `pfm`, распакованный из jar ядра | `.pyfm-runtime` |

Хеш в первом пути выводится из происхождения мода, поэтому два разных jar одного и того же id
мода не делят каталог. Удалять эти каталоги всегда безопасно; они создаются заново при старте.

## 4. Известные ограничения

* **Ничего не запускалось.** Ни клиента, ни выделенного сервера, ни подключения клиента к
  серверу. См. [`testing.ru.md`](testing.ru.md).
* **Компиляции Java здесь не было.** Java-дерево прошло статическую проверку согласованности, а
  не `javac`.
* **Minecraft API не обёрнут.** Девять событий, три хендла, одна точка взаимодействия с Java и
  команды. Нет API реестров, блоков, предметов, экранов, сущностей и датапаков.
* **Только девять событий.** Нет событий отрисовки, нет детализации жизненного цикла сверх
  перечисленного в [`api.ru.md`](api.ru.md) §2.
* **Нет сети.** PyFM не реализует ни пейлоадов, ни каналов, ни синхронизации. Клиент и сервер,
  оба с Python-модами, через PyFM друг с другом не общаются.
* **Нет песочницы.** Python-моды — доверенный код ([`security.ru.md`](security.ru.md)).
* **Нет горячей перезагрузки, интеграции с отладчиком, поддержки IDE.**
* **Только чисто Python'овые wheel** для сторонних пакетов.
* **Точная патч-версия ModDevGradle — заглушка** с пометкой `TODO(verify)` в
  `tools/gen_builds.py`; `projects.neoforged.net` был недоступен.
* **Имена классов событий NeoForge 26.3 не проверены**; использованные имена взяты из ветки
  21.1.
* **Плагин Shadow против Gradle 9.8.2 не проверен.**

## 5. Как сообщить о проблеме

Приложите по порядку:

1. загрузчик и версию Minecraft, а также какую из четырёх комбинаций вы используете;
2. какие из трёх jar PyFM установлены, с точными именами файлов;
3. полный раздел `[PyFM]` из `logs/latest.log`;
4. вывод `python3 tools/validate_metadata.py`, выполненный в проекте вашего мода.

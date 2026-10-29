# apxml-scraper

Скрапер курсов с [apxml.com](https://apxml.com): главы, уроки, текст (HTML и Markdown), формулы (LaTeX), картинки, интерактивные графики (Plotly) и диаграммы (Graphviz).
Результат сохраняется в CSV и/или SQLite.

Перед использованием прочитайте [robots.txt](https://apxml.com/robots.txt) и [Terms of Service](https://apxml.com/pages/terms).
Парсинг разрешён `robots.txt`, но в нём указано `ai-train=no`: не используйте собранный контент для обучения моделей.
Скрапер ходит с паузой между запросами и честным `User-Agent`.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Создайте `.env`:

```env
BASE_URL=https://apxml.com
DELAY=1.5
USER_AGENT=apxml-scraper/0.1 (+https://github.com/<your-name>)
```

| Переменная   | Назначение                                           | По умолчанию        |
|--------------|------------------------------------------------------|---------------------|
| `BASE_URL`   | адрес сайта                                          | обязательна         |
| `DELAY`      | пауза между запросами, секунды                       | `1.5`               |
| `USER_AGENT` | подпись скрапера (контакт необязателен, но вежлив)   | `apxml-scraper/0.1` |

## Запуск

```bash
# один курс -> CSV
python main.py https://apxml.com/courses/introduction-to-deep-learning/

# CSV + SQLite, с загрузкой картинок
python main.py https://apxml.com/courses/introduction-to-deep-learning/ --format csv sqlite --download-images

# несколько курсов за раз
python main.py <url1> <url2> <url3> --format csv sqlite --download-images

# все курсы из sitemap.xml (можно ограничить --limit N)
python main.py --all --format csv sqlite
```

| Флаг                | Описание                                             |
|---------------------|------------------------------------------------------|
| `url ...`           | URL одного или нескольких курсов                     |
| `--all`             | все курсы из sitemap (около 135 курсов, ~7000 страниц) |
| `--limit N`         | с `--all`: только первые N курсов                    |
| `--format ...`      | `csv`, `sqlite` или оба (по умолчанию `csv`)         |
| `--download-images` | скачивать картинки в `output/<курс>/images/`         |
| `--keep-cache`      | не удалять HTML из `cache/` после сохранения курса   |
| `--force`           | перекачать курсы, уже отмеченные как готовые         |
| `-v`                | подробные логи                                       |

Страницы курса кэшируются в `cache/` на время скачивания, а после сохранения курса кэш этого курса удаляется (`--keep-cache` оставляет его).
Готовые курсы записываются в `cache/done.txt`, поэтому прерванный `--all` продолжается с места остановки и не качает готовые курсы заново.
Если часть страниц курса не скачалась, курс не помечается готовым и его кэш остаётся: повторный запуск добирает только недостающее.

## Результат

CSV — `output/<курс>/` (UTF-8 с BOM, открывается в Excel):

| Файл            | Содержимое                                                                   |
|-----------------|------------------------------------------------------------------------------|
| `chapters.csv`  | главы курса                                                                  |
| `lessons.csv`   | уроки: тип (`lesson`/`practice`/`quiz`), заголовок, `content_markdown`, `content_html` |
| `images.csv`    | картинки уроков (URL, alt, локальный путь)                                   |
| `charts.csv`    | графики и диаграммы: `kind` (`plotly` — JSON data+layout, `graphviz` — DOT-код) |

SQLite — `output/apxml.db`, те же таблицы (`courses`, `chapters`, `lessons`, `images`, `charts`) для всех курсов сразу.
Повторное сохранение курса заменяет его строки.

Связи: `course_slug` → `chapter_slug` → `lesson_slug`.

В Markdown формулы записаны как `$...$` и `$$...$$` (LaTeX), а графики и диаграммы заменены маркером `[plotly: <id>]` или `[graphviz: <id>]`; их исходник лежит в `charts`.

Тесты (quiz) на сайте доступны только после входа, поэтому сохраняется лишь их описание.

## Архитектура

```
Fetcher -> Parser -> модели (dataclass) -> Storage
```

```
main.py                    CLI
scraper/
  config.py                Settings из .env
  models.py                Course, Chapter, Lesson, Image, Chart
  pipeline.py              CourseScraper: связывает слои (внедрение зависимостей)
  discovery.py             поиск всех курсов в sitemap.xml
  images.py                ImageDownloader
  fetchers/                BaseFetcher -> HttpFetcher (delay, retry), CachedFetcher (кэш на диске)
  parsers/                 BaseParser -> CoursePageParser, LessonPageParser
  storage/                 BaseStorage -> CsvStorage, SqliteStorage; factory.py
utils/url.py               нормализация URL, slug курса
```

### Добавить новый формат вывода

1. Создайте класс-наследник `BaseStorage` с методом `save(course)` в `scraper/storage/`.
2. Зарегистрируйте его в `scraper/storage/factory.py` (`FORMATS` и `get_storage`).
3. Запускайте с `--format <имя>`.

Остальной код менять не нужно.

## Скорость и возобновление

Сайт отвечает за 1-2.5 с на страницу, поэтому курс из ~70 уроков качается около 3-10 минут, а `--all` (около 7000 страниц) — 3-4 часа.
Если запуск прервали (закрыли ноутбук, пропал интернет), достаточно повторить ту же команду: готовые курсы пропускаются, а недокачанный продолжается из кэша.
Для оценки места: результат всех курсов занимает ~250 МБ в `output/`, а кэш одного курса — 20-40 МБ и удаляется после сохранения.

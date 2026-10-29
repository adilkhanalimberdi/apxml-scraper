# apxml-scraper

Скрапер курсов с [apxml.com](https://apxml.com): главы, уроки, текст (HTML и Markdown), формулы (LaTeX), картинки и интерактивные графики (Plotly).
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

# все курсы из sitemap.xml (можно ограничить --limit N)
python main.py --all --format csv sqlite
```

| Флаг                | Описание                                             |
|---------------------|------------------------------------------------------|
| `url`               | URL курса                                            |
| `--all`             | все курсы из sitemap (около 135 курсов, ~7000 страниц) |
| `--limit N`         | с `--all`: только первые N курсов                    |
| `--format ...`      | `csv`, `sqlite` или оба (по умолчанию `csv`)         |
| `--download-images` | скачивать картинки в `output/<курс>/images/`         |
| `-v`                | подробные логи                                       |

Все страницы кэшируются в `cache/`, поэтому повторный запуск не ходит на сайт заново (прерванный `--all` продолжается с места остановки).
Чтобы перекачать страницу, удалите её файл из `cache/`.

## Результат

CSV — `output/<курс>/` (UTF-8 с BOM, открывается в Excel):

| Файл            | Содержимое                                                                   |
|-----------------|------------------------------------------------------------------------------|
| `chapters.csv`  | главы курса                                                                  |
| `lessons.csv`   | уроки: тип (`lesson`/`practice`/`quiz`), заголовок, `content_markdown`, `content_html` |
| `images.csv`    | картинки уроков (URL, alt, локальный путь)                                   |
| `charts.csv`    | интерактивные графики: Plotly-JSON (data + layout)                           |

SQLite — `output/apxml.db`, те же таблицы (`courses`, `chapters`, `lessons`, `images`, `charts`) для всех курсов сразу.
Повторное сохранение курса заменяет его строки.

Связи: `course_slug` → `chapter_slug` → `lesson_slug`.

В Markdown формулы записаны как `$...$` и `$$...$$` (LaTeX), а графики заменены маркером `[chart: <id>]`; сам график лежит в `charts`.

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

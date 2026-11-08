# HOME_LIT_LIB — домашняя библиотека

Учебный проект: система учёта книг с двумя интерфейсами — консольным (CLI) и веб (FastAPI). Реализации разбиты на изолированные архитектуры (`arch1`, `arch2`, …). Общие для всех — исходные данные `books.csv`, файлы баз и конфиг в корне.

## Структура

    <корень>/
      .gitignore
      config.ini                # конфигурация (коммитим)
      books.csv                 # исходные данные (98 записей)
      library_dev.db            # создаётся в рантайме, в git не попадает
      library_test.db           # LIBRARY_ENV=test
      library_prod.db           # LIBRARY_ENV=prod
      README.md
      arch1/
        book.py                 # модель Book
        repository.py           # SQLite: схема, CRUD, импорт CSV, поиск, сортировка, статистика
        service.py              # правила/валидация поверх репозитория
        export.py               # отчёты и выгрузки (TXT/HTML), чистые функции
        config.py               # загрузчик config.ini
        cli.py                  # консольное меню
        main.py                 # точка входа CLI
        web.py                  # точка входа веба (FastAPI)
        requirements.txt        # зависимости только для веба
        templates/
          base.html             # общий каркас
          index.html            # дашборд
          books.html            # список книг
          book.html             # карточка книги
          book_form.html        # форма добавления/редактирования
          search.html           # поиск
          stats.html            # статистика
        static/
          style.css             # стиль «библиотека» (дерево/пергамент/золото)
        checks/
          __init__.py
          __main__.py           # раннер: находит и запускает *_checks.py
          _helpers.py           # mk_book — Book с дефолтами
          _db_helpers.py        # new_repo / new_service — временная база
          book_checks.py        # 11 проверок
          repository_checks.py  # 27 проверок
          service_checks.py     # 11 проверок
          export_checks.py      # 8 проверок
          cli_checks.py         # 7 проверок
          config_checks.py      # 14 проверок

Всего: 78 проверок.

## Конфигурация (`config.ini` в корне)

    [app]
    env = dev

    [ui]
    page_size = 30

    [data]
    csv_path = books.csv

    [export]
    export_dir = ~/Загрузки

    [web]
    host = 127.0.0.1
    port = 8001

| Ключ | Значения | Назначение |
|---|---|---|
| `app.env` | `dev` / `test` / `prod` | режим (какая база используется) |
| `ui.page_size` | `15` / `30` / `50` / `100` | размер страницы в просмотре и статистике |
| `data.csv_path` | путь | CSV для импорта; относительный — от корня проекта |
| `export.export_dir` | путь | папка для отчётов CLI; `~` раскрывается; должна существовать |
| `web.host` | адрес | адрес веб-сервера |
| `web.port` | 1–65535 | порт веб-сервера (по умолчанию 8001) |

**Приоритет режима:** `LIBRARY_ENV=prod python …` (env) > `config.ini` (`app.env`) > `"dev"`.

**Приоритет веба:** `WEB_HOST` / `WEB_PORT` (env) > `config.ini` (`[web]`) > дефолты (`127.0.0.1`, `8001`).

**Обязательность `export.export_dir`:** если ключ не задан, папки нет или это не директория — `ValueError` при старте (fail fast).

**Невалидные значения** (`env = prodd`, `page_size = 25`, `port = 99999`) → `ValueError` при старте.

## Файлы

### `.gitignore` (в корне)

Не попадают: `.idea/`, `__pycache__/`, `*.py[cod]`, `.venv/`, `venv/`, `env/`, `*.db`, `*.sqlite`, `*.sqlite3`, `.DS_Store`, `Thumbs.db`, сгенерированные: `report_*.txt`, `report_*.html`, `dump_*.txt`, `dump_*.html`.

`books.csv` и `config.ini` **не** игнорируются. Проверка: `git check-ignore -v books.csv config.ini` ничего не выводит.

### `books.csv` (в корне)

98 записей, по две книги на автора. Формат: поля в двойных кавычках через `", "`, запись завершается `;\n`, UTF-8. Заголовки: `Фамилия, Имя, Отчество, Название, Год, Жанр, Город, Издание`. Пустые поля — `""`. `Фамилия` заполнена всегда.

### Базы данных

Три файла в корне, выбираются по режиму:

    python3 arch1/main.py                     # dev (по умолчанию)
    LIBRARY_ENV=test python3 arch1/main.py
    LIBRARY_ENV=prod python3 arch1/main.py

Создаются автоматически при первом запуске. В git не попадают (`*.db`). Импорт CSV в `main.py`/`web.py` **не** выполняется: пользователь делает это явно через CLI (пункт 6), поэтому первый запуск даёт пустую базу. CLI и веб используют **одну и ту же базу** (по `ENV`).

### `arch1/book.py` — модель

`@dataclass class Book` с полями `last_name`, `first_name`, `middle_name`, `title`, `year`, `genre`, `city`, `publisher`, `id` (последним, `= None`). Необязательные — `Optional[...]`. `@property author` склеивает непустые части ФИО. `__str__` даёт `[id] Автор — Название (год, жанр)`: год и жанр добавляются, если заданы; если нет ни того, ни другого — `(—)`.

В `book.py` нет SQL, валидации и `input()/print()`.

### `arch1/repository.py` — слой хранения

`SqliteBookRepository`:

- `__init__(db_path)` — соединение, `row_factory = sqlite3.Row`, регистрация `py_lower` (кириллица в `LIKE`; `LOWER` в SQLite работает только для ASCII);
- `create_schema`, `drop`, `close`, `count`;
- `import_csv(path)` — разбор нестандартного CSV (`;\n` → `\n`), пустые необязательные поля → `None`, битый год → `None`, строки без фамилии/названия пропускаются;
- `add`, `get`, `update`, `delete`;
- `list_all()` — `ORDER BY last_name, first_name, title`;
- `list_all_with_sort(sort_by, reverse)` — ключи `author` (по `last_name`), `title`, `year`, `genre`, `id`; `NULL` всегда в конце; неизвестный ключ → `ValueError`;
- `find_by_author(substr)` — по склейке ФИО через `py_lower(...) LIKE ?`; `find_by_title`, `find_by_genre` — по одному полю; `find_by_year_range(from, to)`; `find_by_id`; `find_any(query)` — по 7 текстовым полям через `OR LIKE` + `year = ?`/`id = ?`, если `query` — число;
- `count_by_genre()`, `count_by_author()` — `GROUP BY`, `ORDER BY cnt DESC`;
- `_row_to_book(row)`.

Модульная `validate_csv(path)` — проверка структуры файла перед импортом: существует, файл, UTF-8, в заголовке есть `Фамилия` и `Название`.

Сортировка в SQL. Ключи `sort_by` — белый список `_SORT_EXPRESSIONS`, в SQL подставляются только литералы и `ASC`/`DESC`. Пользовательский ввод в SQL не попадает.

### `arch1/service.py` — слой правил

`LibraryService(repo)`:

- `_validate(book)` — фамилия/название не пустые, год либо `None`, либо `int` в `[-3000, 2100]`;
- `add_book`, `update_book` (требует `id`), `get_book`, `delete_book`;
- `list_books(sort_by=None, reverse=False)`;
- `search_by_author`, `search_by_title`, `search_by_genre`, `search_by_year(from, to)`, `search_by_id`, `search_any`;
- `stats_by_genre()`, `stats_by_author()`;
- `import_csv(path)`, `count()`, `clear_all()`.

Репозиторий передаётся в конструктор (инверсия управления).

### `arch1/export.py` — отчёты и выгрузки

Чистые функции, `generated_at` передаётся снаружи.

- `report_txt(total, genre_rows, author_rows, generated_at)` — текст: «Домашняя библиотека — отчёт», дата, всего книг, две секции с процентами, заголовки по центру.
- `report_html(...)` — HTML в стиле «библиотека»: тёмное дерево, пергамент, двойная золотая рамка, бордовые шапки, `small-caps`, `❦`. `html.escape` для всех строк.
- `dump_txt(books, generated_at)` — таблица 10 полей через `" | "`, `—` для `None`.
- `dump_html(books, generated_at)` — тот же стиль, таблица 10 колонок, `.table-wrap` с `overflow-x: auto`.

`export.py` самодостаточен: HTML-отчёты и выгрузки содержат встроенный `<style>`, не зависят от `static/style.css`.

### `arch1/config.py` — загрузчик конфигурации

- `load_config(path)` — читает INI, возвращает `{'env', 'page_size', 'csv_path', 'export_dir', 'web_host', 'web_port'}`. Проверки всех значений, `ValueError` с понятным текстом.
- `resolve_env(cli_env, file_cfg)` — `LIBRARY_ENV` > `config.ini` > `"dev"`.
- `resolve_web(env_host, env_port, file_cfg)` — `WEB_HOST`/`WEB_PORT` > `config.ini` > дефолты.

### `arch1/cli.py` — консольный интерфейс

`ConsoleUI(service, csv_path, page_size, export_dir)`. Меню:

    1) Показать все книги
    2) Найти книгу или книги
    3) Добавить книгу
    4) Редактировать книгу
    5) Удалить книгу
    6) Импортировать из CSV
    7) Очистить базу данных (drop)
    8) Статистика
    9) Экспорт
    10) Выход

- **Просмотр (1)** — сортировка (`author`/`title`/`year`/`genre`/`id`), направление (`y/N`, Enter — возрастание), пагинация (размер из конфига, меняется `[S]`).
- **Поиск (2)** — по полю или по всем полям; год с диапазоном `1800-1900`.
- **Добавление (3)** — обязательные поля переспрашиваются, остальные пустой ввод → `None`, `ValueError` → `Ошибка: ...`.
- **Редактирование (4) / удаление (5)** — поиск → результаты → `[E]`/`[D]`; в удалении `[D]` открывает массовый ввод `1, 5, 10-24`.
- **Импорт (6)** — путь (Enter → конфиг), `validate_csv`, `A`/`R`/`N`.
- **Очистка (7)** — два подтверждения (`[y/N]` и `yes`).
- **Статистика (8)** — жанры/авторы, `[C]` открывает меню критериев.
- **Экспорт (9)** — отчёт/выгрузка, TXT/HTML, файлы пишутся в `export_dir`.

**Пагинация** (`_paginate`) — общая: `[N/Enter]/[P]/[G]/[S]/[E]/[D]/[F]/[C]/[Q]`. После `[E]`/`[D]` список перечитывается; `[F]` подменяет `loader` без выхода; `[C]` меняет критерий статистики.

### `arch1/web.py` — веб-интерфейс (FastAPI)

`app = FastAPI(...)`, `StaticFiles` на `/static`, `Jinja2Templates` на `arch1/templates`. `get_service()` — генератор с `Depends`: открывает `SqliteBookRepository` на запрос, закрывает после ответа.

**Read-only (7):**

| Маршрут | Что |
|---|---|
| `GET /` | дашборд: всего книг, топ-5 жанров/авторов |
| `GET /books?sort=&reverse=&page=&size=` | список с сортировкой и пагинацией |
| `GET /books/{id}?back=` | карточка книги |
| `GET /search?field=&q=&page=&size=` | поиск с пагинацией |
| `GET /stats?kind=genre\|author` | статистика |
| `GET /report` | HTML-отчёт (открывается) |
| `GET /report/download` | скачать HTML-отчёт |
| `GET /report.txt` | скачать TXT-отчёт |
| `GET /dump` | скачать HTML-выгрузку |
| `GET /dump.txt` | скачать TXT-выгрузку |

**CRUD (5):**

| Маршрут | Что |
|---|---|
| `GET /books/new?back=` | форма «Добавить» |
| `POST /books` | создать, редирект на `/books/{id}?back=` |
| `GET /books/{id}/edit?back=` | форма «Редактировать» |
| `POST /books/{id}/edit` | обновить, редирект на `/books/{id}?back=` |
| `POST /books/{id}/delete?back=` | удалить, редирект на `back` |

**Порядок маршрутов:** `GET /books/new` объявлен **раньше** `GET /books/{id}` — иначе `"new"` пытается превратиться в `int` и даёт 422.

**Кнопка «← К списку»:** параметр `?back=` таскает исходный URL (список с сортировкой/страницей или поиск с запросом). Карточка, форма, «Отмена», «Редактировать», «Удалить» — все носят `back` с собой. Из `/books?sort=id&page=3` вернётесь туда же; из `/search?q=...` — в поиск с тем же запросом.

**Ошибки валидации** (пустая фамилия, год-не-число): форма показывается снова с красным сообщением, введённые значения сохраняются.

**Запуск:**

    cd arch1
    python3 web.py

или с авто-перезапуском при правках:

    cd arch1
    uvicorn web:app --port 8001 --reload

Порт по умолчанию 8001 (8000 может быть занят). Переопределяется `WEB_PORT` / `[web] port`.

### `arch1/main.py` — точка входа CLI

    BASE_DIR = Path(__file__).resolve().parent.parent
    cfg = load_config(BASE_DIR / "config.ini")
    ENV = resolve_env(os.getenv("LIBRARY_ENV"), cfg)
    DB_PATH = DB_PATHS[ENV]
    CSV_PATH = BASE_DIR / cfg["csv_path"]

    repo = SqliteBookRepository(str(DB_PATH))
    repo.create_schema()
    service = LibraryService(repo)
    ConsoleUI(service, CSV_PATH, page_size=cfg["page_size"],
              export_dir=cfg["export_dir"]).run()

`main.py` не содержит логики: только пути, чтение конфига и сборка зависимостей. `web.py` собирает **те же** `repo`/`service` (через `Depends`) и отдаёт шаблонам.

### `arch1/requirements.txt` — зависимости веба

    fastapi>=0.110
    uvicorn[standard]>=0.27
    jinja2>=3.1
    python-multipart>=0.0.9

`python-multipart` нужен FastAPI для `Form(...)` — без него `RuntimeError` при старте. CLI работает **без** этих пакетов (только stdlib).

Установка:

    pip install -r arch1/requirements.txt

### `arch1/templates/` — шаблоны Jinja2

- `base.html` — каркас: `<head>`, `<link rel="stylesheet" href="/static/style.css">`, `<h1>Домашняя библиотека</h1>`, навигация (Главная, Книги, Поиск, Статистика), `{% block content %}`, footer.
- `index.html` — дашборд: режим/база/всего, топ-5 жанров и авторов, кнопки.
- `books.html` — «+ Добавить книгу», таблица с кликабельными заголовками для сортировки, пагинация, выбор размера.
- `book.html` — карточка со всеми полями, «← К списку» (`back`), «Редактировать», «Удалить» (`onsubmit="return confirm(...)"`).
- `book_form.html` — одна форма для add/edit: `required` на обязательных, `action` разный, при ошибке — поля с введёнными значениями.
- `search.html` — форма (select поля, input, кнопка), результаты с пагинацией, `field`/`q`/`size` сохраняются в ссылках (`q|urlencode`).
- `stats.html` — панель экспорта справа сверху (2×2: «Отчёт (HTML)», «Отчёт (TXT)», «Выгрузка БД (HTML)», «Выгрузка БД (TXT)»), переключатель «По жанрам / По авторам», таблица с процентами.

### `arch1/static/style.css` — стиль «библиотека»

Тёмный деревянный фон (`repeating-linear-gradient` + `radial-gradient`), пергаментная карточка с двойной золотой рамкой (`outline: double`), бордовые шапки таблиц, золотой текст, `small-caps`, `❦` по бокам заголовка. Кнопки: `.btn` (тёмно-бордовая), `.btn.secondary` (светлая), `.btn.gold` (золотая, выгрузки), `.btn.danger` (тёмно-красная, удаление). Адаптивность `@media (max-width: 700px)`.

`static/style.css` **и** встроенный `<style>` в `export.py` выглядят похоже — это **сознательное совпадение**: `export.py` остаётся самодостаточным (открывается без папки `static/`), а шаблоны используют внешний CSS. Правка стиля в одном месте не автоматически переносится в другое — это осознанный компромисс.

## Проверки (checks)

Живут в `arch1/checks/`, по модулю на файл. Раннер `checks/__main__.py` находит все `*_checks.py` через `pkgutil.iter_modules` и вызывает `check_*`.

    book_checks.py        11
    repository_checks.py  27
    service_checks.py     11
    export_checks.py       8
    cli_checks.py          7
    config_checks.py      14
    -------------------------
    всего                 78

### Почему `python -m checks`, а не `python checks/__main__.py`

При прямом запуске файла Python кладёт в `sys.path` папку `checks/`, а не `arch1/`. Импорт `from book import Book` падает. `python -m checks` запускается **из `arch1/`**, и `arch1/` попадает в `sys.path`.

    cd arch1
    python3 -m checks

Ожидаемо: 78 строк `OK` и `Все проверки прошли: 78`.

### Временные базы

Проверки, которым нужна база, работают с временной (`tempfile.TemporaryDirectory()` в `/tmp/tmpXXXXXXXX/checks.db`), а не с `library_dev/test/prod.db`. Каждая создаёт свою через `_db_helpers.new_repo()`/`new_service()`, в `finally` — `repo.close()`, `tmp.cleanup()`. `config_checks.py` использует `NamedTemporaryFile` для временных `.ini`.

### Что **не** покрыто проверками

`web.py` (маршруты, `TemplateResponse`, `Form`), `cli.py` (кроме `_parse_id_spec`), `main.py`, `__main__.py`, `_helpers.py`, `_db_helpers.py`. Это I/O и инфраструктура: автоматические проверки потребовали бы `TestClient`/`httpx` и моков (интеграционные тесты), что выходит за рамки «проверок в процессе разработки». Маршруты веба и меню CLI проверяются **ручным прогоном** (сценарии в README/refer).

## Как это работает вместе

**Запуск CLI:** `main.py` читает `config.ini` → `resolve_env` → выбирает базу → `create_schema` → `ConsoleUI.run()`.

**Запуск веба:** `web.py` при импорте читает `config.ini`, `resolve_env`, `resolve_web`; на каждый запрос `get_service()` открывает соединение, отдаёт `LibraryService`, после ответа закрывает.

**Добавление (CLI):** `cli.py` спрашивает поля → `service.add_book` валидирует → `repo.add` (`INSERT`) → id возвращается → подтверждение.

**Добавление (веб):** `GET /books/new` → форма → `POST /books` (Form) → `_parse_year` → `Book(...)` → `service.add_book` → при успехе `303` на `/books/{id}?back=...`; при `ValueError` — форма снова с ошибкой и введёнными значениями.

**Просмотр:** `service.list_books(sort_by, reverse)` → `repo.list_all_with_sort` (`ORDER BY`) → список `Book` → пагинация (CLI — своя, веб — `page`/`size` из URL).

**Поиск:** `service.search_*` → `repo.find_*` (`LIKE`/`=`) → список `Book` → пагинация.

**Статистика:** `service.stats_*` → `repo.count_by_*` (`GROUP BY`) → пары `(label, cnt)` → проценты на стороне интерфейса.

**Экспорт (CLI):** `export.report_*`/`dump_*` → строка → `Path(export_dir) / "..."` → `write_text(encoding="utf-8")`.

**Экспорт (веб):** те же `export.*` → `PlainTextResponse`/`HTMLResponse` с `Content-Disposition: attachment` → браузер скачивает. `/report` без `Content-Disposition` — открывается в браузере.

**Возврат «← К списку»:** ссылки на карточку содержат `?back=<исходный URL>`, карточка/форма носят `back` через кнопки, «← К списку» ведёт по нему. Работает без сессий и `Referer`.

## Известные ограничения

- Пагинация клиентская: сервис возвращает весь список, интерфейс режет. Для 10 000 записей нормально; для миллионов — `LIMIT/OFFSET` в репозитории.
- `list_all_with_sort(sort_by="author")` — только по `last_name`; внутри одного автора — порядок вставки. `find_by_author` — по склейке ФИО (поиск ищет человека, сортировка — по фамилии).
- Импорт в CLI в режиме `A` не проверяет дубликаты: `98 + 98 = 196`. Для замены — `R`.
- «Автор неизвестен» — строка в `last_name`; отдельного `is_anonymous` нет.
- `BookRepositoryProtocol` — на заметке.
- Массовое удаление (`1, 5, 10-24`) — только в CLI; в вебе — по одной.
- Экспорт CLI не спрашивает путь: всегда `export_dir`, повторный экспорт перезаписывает. Экспорт веба — скачивание, имя `report_N_books.*`/`dump_N_books.*`.
- HTML-отчёты `export.py` и `static/style.css` — два независимых источника стиля (сознательно, чтобы `export.py` был самодостаточным).
- `web.py` и `cli.py` не покрыты автоматическими проверками (I/O; см. «Что не покрыто»).

## Запуск

**CLI:**

    cd <корень>
    python3 arch1/main.py

Первый запуск: `library_dev.db` создаётся пустой. Импорт данных — пункт `6` → Enter → `R`.

**Веб:**

    pip install -r arch1/requirements.txt      # один раз
    cd <корень>/arch1
    python3 web.py

Открыть `http://127.0.0.1:8001/`. Те же данные, что в CLI (общая база по `ENV`). Если база пуста — сначала импорт через CLI (пункт 6), потом обновить страницу.

#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from book import Book
from export import report_txt, report_html, dump_txt, dump_html
from repository import validate_csv
from service import LibraryService, YEAR_MIN, YEAR_MAX

PAGE_SIZES = (15, 30, 50, 100)


class ConsoleUI:
    def __init__(self, service: LibraryService, csv_path: Path,
                 page_size: int, export_dir: Path):
        self.service = service
        self.csv_path = csv_path
        self.page_size = page_size
        self.export_dir = export_dir

    # ---------- главный цикл ----------
    def run(self) -> None:
        while True:
            self._print_menu()
            choice = input("Выбор: ").strip()
            if choice == "1":
                self._show_all()
            elif choice == "2":
                self._search()
            elif choice == "3":
                self._add()
            elif choice == "4":
                self._edit()
            elif choice == "5":
                self._delete()
            elif choice == "6":
                self._import()
            elif choice == "7":
                self._drop()
            elif choice == "8":
                self._stats()
            elif choice == "9":
                self._export()
            elif choice == "10" or choice.lower() == "q":
                print("До встречи.")
                return
            else:
                print("Не понял выбор, попробуйте ещё раз")

    def _print_menu(self) -> None:
        print()
        print("=== Домашняя библиотека ===")
        print("1) Показать все книги")
        print("2) Найти книгу или книги")
        print("3) Добавить книгу")
        print("4) Редактировать книгу")
        print("5) Удалить книгу")
        print("6) Импортировать из CSV")
        print("7) Очистить базу данных (drop)")
        print("8) Статистика")
        print("9) Экспорт")
        print("10) Выход")

    # ---------- просмотр и пагинация ----------
    def _show_all(self) -> None:
        if self.service.count() == 0:
            print("Библиотека пуста")
            return
        print("Сортировка: [1] автор  [2] название  [3] год  [4] жанр  [5] id  [Enter] по автору")
        choice = input("> ").strip()
        sort_map = {"1": "author", "2": "title", "3": "year", "4": "genre", "5": "id", "": "author"}
        sort_by = sort_map.get(choice, "author")
        reverse = input("По убыванию? [y/N, Enter — по возрастанию]: ").strip().lower() == "y"
        self._paginate(
            loader=lambda: self.service.list_books(sort_by=sort_by, reverse=reverse),
        )

    def _paginate(self, loader, mode: str = "view",
                  empty_message: str = "Библиотека пуста",
                  formatter: Callable[[Any], str] = str,
                  allow_actions: bool = True,
                  header: str | None = None,
                  switcher: Callable | None = None,
                  switch_hint: Callable[[], str] | None = None) -> None:
        page = 1
        if header:
            print(f"\n{header}")
        while True:
            items = loader()
            total = len(items)
            if total == 0:
                print(empty_message)
                return
            total_pages = (total + self.page_size - 1) // self.page_size
            if page > total_pages:
                page = total_pages
            start = (page - 1) * self.page_size
            chunk = items[start:start + self.page_size]

            print()
            print(f"--- Страница {page}/{total_pages} "
                  f"(всего {total}, по {self.page_size}) ---")
            for item in chunk:
                print(f"  {formatter(item)}")
            print()

            print("[N/Enter] следующая  [P] предыдущая  [G] страница  [S] размер")
            parts = []
            if allow_actions:
                parts.append("[E] редактировать")
                parts.append("[D] удалить (1 / список / диапазон)"
                             if mode == "delete" else "[D] удалить")
                parts.append("[F] новый поиск")
            if switcher is not None and switch_hint is not None:
                parts.append(f"[C] {switch_hint()}")
            parts.append("[Q] выход")
            print("  ".join(parts))

            cmd = input("> ").strip().upper()
            if cmd in ("N", ""):
                if page < total_pages:
                    page += 1
                else:
                    print("Это последняя страница")
            elif cmd == "P":
                if page > 1:
                    page -= 1
                else:
                    print("Это первая страница")
            elif cmd == "G":
                try:
                    p = int(input(f"Номер страницы (1-{total_pages}): ").strip())
                except ValueError:
                    print("Нужно число")
                    continue
                if 1 <= p <= total_pages:
                    page = p
                else:
                    print("Нет такой страницы")
            elif cmd == "S":
                new_size = self._ask_page_size()
                if new_size:
                    self.page_size = new_size
                    page = 1
            elif cmd == "C" and switcher is not None:
                result = switcher()
                if result is not None:
                    loader, formatter, new_header = result
                    page = 1
                    if new_header:
                        print(f"\n{new_header}")
            elif cmd == "E" and allow_actions:
                self._edit_book_by_id()
            elif cmd == "D" and allow_actions:
                if mode == "delete":
                    self._delete_group()
                else:
                    self._delete_by_id()
            elif cmd == "F" and allow_actions:
                new_loader = self._pick_search_loader()
                if new_loader is not None:
                    loader = new_loader
                    page = 1
            elif cmd == "Q":
                return
            else:
                print("Не понял команду")

    # ---------- поиск ----------
    def _search(self) -> None:
        loader = self._pick_search_loader()
        if loader is None:
            return
        self._paginate(loader=loader, empty_message="Ничего не найдено")

    def _pick_search_loader(self):
        """Возвращает функцию-загрузчик list[Book] или None при отмене."""
        print("\nПоиск: [1] по конкретному полю  [2] по всем полям  [Enter] отмена")
        mode = input("> ").strip()
        if mode == "":
            return None
        if mode == "1":
            return self._pick_field_loader()
        if mode == "2":
            query = input("Что искать: ").strip()
            if not query:
                print("Параметры поиска не выбраны")
                return None
            return lambda: self.service.search_any(query)
        print("Не понял выбор")
        return None

    def _pick_field_loader(self):
        print("Поле: [1] автор  [2] название  [3] год  [4] жанр  [5] id  [Enter] отмена")
        field = input("> ").strip()
        if field == "":
            return None
        if field == "1":
            substr = input("Автор (подстрока): ").strip()
            if not substr:
                print("Параметры поиска не выбраны")
                return None
            return lambda: self.service.search_by_author(substr)
        if field == "2":
            substr = input("Название (подстрока): ").strip()
            if not substr:
                print("Параметры поиска не выбраны")
                return None
            return lambda: self.service.search_by_title(substr)
        if field == "3":
            raw = input("Год (1833 или 1800-1900): ").strip()
            if not raw:
                print("Параметры поиска не выбраны")
                return None
            try:
                if "-" in raw:
                    a, b = raw.split("-", 1)
                    yf, yt = int(a), int(b)
                else:
                    yf = yt = int(raw)
            except ValueError:
                print("Год должен быть числом или диапазоном a-b")
                return None
            return lambda: self.service.search_by_year(yf, yt)
        if field == "4":
            substr = input("Жанр (подстрока): ").strip()
            if not substr:
                print("Параметры поиска не выбраны")
                return None
            return lambda: self.service.search_by_genre(substr)
        if field == "5":
            raw = input("id: ").strip()
            if not raw:
                print("Параметры поиска не выбраны")
                return None
            try:
                book_id = int(raw)
            except ValueError:
                print("id должен быть числом")
                return None
            return lambda: self.service.search_by_id(book_id)
        print("Не понял выбор")
        return None

    # ---------- добавление ----------
    def _add(self) -> None:
        print("\nНовая книга (Enter — пропустить необязательное):")
        book = Book(
            last_name=self._ask_required("Фамилия"),
            first_name=self._ask_optional("Имя"),
            middle_name=self._ask_optional("Отчество"),
            title=self._ask_required("Название"),
            year=self._ask_year(),
            genre=self._ask_optional("Жанр"),
            city=self._ask_optional("Город"),
            publisher=self._ask_optional("Издание"),
        )
        try:
            new_id = self.service.add_book(book)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return
        print(f"Добавлено с id={new_id}: {self.service.get_book(new_id)}")

    # ---------- редактирование ----------
    def _edit(self) -> None:
        loader = self._pick_search_loader()
        if loader is None:
            return
        self._paginate(loader, empty_message="Ничего не найдено")

    def _edit_book_by_id(self) -> None:
        raw = input("id книги для редактирования: ").strip()
        if not raw:
            return
        try:
            book_id = int(raw)
        except ValueError:
            print("id должен быть числом")
            return
        book = self.service.get_book(book_id)
        if book is None:
            print(f"Книга с id={book_id} не найдена")
            return
        self._edit_book(book)

    def _edit_book(self, book: Book) -> None:
        print("\nТекущие значения (Enter — оставить как есть):")
        print(self._format_book_full(book))
        print()
        book.last_name = self._ask_required("Фамилия", book.last_name)
        book.first_name = self._ask_optional("Имя", book.first_name)
        book.middle_name = self._ask_optional("Отчество", book.middle_name)
        book.title = self._ask_required("Название", book.title)
        book.year = self._ask_year(book.year)
        book.genre = self._ask_optional("Жанр", book.genre)
        book.city = self._ask_optional("Город", book.city)
        book.publisher = self._ask_optional("Издание", book.publisher)
        try:
            self.service.update_book(book)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return
        print(f"Обновлено: {self.service.get_book(book.id)}")

    # ---------- удаление ----------
    def _delete(self) -> None:
        loader = self._pick_search_loader()
        if loader is None:
            return
        self._paginate(loader, mode="delete", empty_message="Ничего не найдено")

    def _delete_by_id(self) -> None:
        raw = input("id книги для удаления: ").strip()
        if not raw:
            return
        try:
            book_id = int(raw)
        except ValueError:
            print("id должен быть числом")
            return
        book = self.service.get_book(book_id)
        if book is None:
            print(f"Книга с id={book_id} не найдена")
            return
        print(f"Удалить: {book}?")
        if input("[y/N]: ").strip().lower() != "y":
            print("Отменено")
            return
        self.service.delete_book(book_id)
        print(f"Удалено (id={book_id})")

    def _delete_group(self) -> None:
        print()
        print("Можно указать один id, несколько через запятую или диапазон через '-'.")
        print("Примеры: '5'  '1, 5, 10'  '10-24'  '1, 5, 10-24'")
        raw = input("id для удаления (Enter — отмена): ").strip()
        if not raw:
            return
        ids = self._parse_id_spec(raw)
        if not ids:
            print("Не удалось разобрать id")
            return
        existing = [i for i in ids if self.service.get_book(i) is not None]
        missing = [i for i in ids if i not in existing]
        if not existing:
            print(f"Ни одной из указанных книг нет в базе: {ids}")
            return
        print(f"\nБудет удалено {len(existing)} книг: {existing}")
        if missing:
            print(f"Пропущено (нет в базе): {missing}")
        if input("Подтвердить? [y/N]: ").strip().lower() != "y":
            print("Отменено")
            return
        for i in existing:
            self.service.delete_book(i)
        print(f"Удалено: {len(existing)}")

    @staticmethod
    def _parse_id_spec(spec: str) -> list[int]:
        result = set()
        for token in spec.replace(" ", "").split(","):
            if not token:
                continue
            if "-" in token:
                parts = token.split("-", 1)
                try:
                    start, end = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                if start > end:
                    start, end = end, start
                result.update(range(start, end + 1))
            else:
                try:
                    result.add(int(token))
                except ValueError:
                    continue
        return sorted(result)

    # ---------- импорт ----------
    def _import(self) -> None:
        raw = input(f"Путь к CSV (Enter — {self.csv_path.name}): ").strip()
        path = Path(raw) if raw else self.csv_path
        ok, err = validate_csv(str(path))
        if not ok:
            print(f"Ошибка: {err}")
            return
        current = self.service.count()
        print(f"Файл: {path}")
        print(f"Сейчас в базе: {current} записей")
        print("Добавить [A] / Заменить базу [R] / Отмена [N]")
        mode = input("> ").strip().upper()
        if mode in ("", "N"):
            print("Отменено")
            return
        if mode == "R":
            self.service.clear_all()
            print("База очищена")
        elif mode != "A":
            print("Не понял команду, отменено")
            return
        try:
            n = self.service.import_csv(str(path))
        except Exception as e:
            print(f"Ошибка импорта: {e}")
            return
        print(f"Импортировано: {n}, всего в базе: {self.service.count()}")

    # ---------- очистка ----------
    def _drop(self) -> None:
        n = self.service.count()
        if n == 0:
            print("База уже пуста")
            return
        print(f"В базе {n} записей.")
        print("Это действие необратимо: все книги будут удалены.")
        if input("Вы уверены, что хотите стереть базу данных целиком? [y/N]: ").strip().lower() != "y":
            print("Отменено")
            return
        if input("Введите 'yes' для окончательного подтверждения: ").strip() != "yes":
            print("Отменено")
            return
        self.service.clear_all()
        print(f"База очищена, записей: {self.service.count()}")

    # ---------- статистика ----------
    def _stats(self) -> None:
        if self.service.count() == 0:
            print("Библиотека пуста")
            return

        # Список критериев. Чтобы добавить новый — дописать сюда одну строку.
        criteria = [
            ("1", "по жанрам", "genre"),
            ("2", "по авторам", "author"),
        ]

        total = self.service.count()
        genre_rows = self.service.stats_by_genre()
        author_rows = self.service.stats_by_author()

        def make(kind: str):
            if kind == "genre":
                data = [((g if g else "(без жанра)"), cnt, cnt / total * 100)
                        for g, cnt in genre_rows]
                return (lambda: data, fmt,
                        f"=== Статистика: По жанрам (всего книг: {total}) ===")
            if kind == "author":
                data = [(a, cnt, cnt / total * 100) for a, cnt in author_rows]
                return (lambda: data, fmt,
                        f"=== Статистика: По авторам (всего книг: {total}) ===")
            raise ValueError(f"Неизвестный критерий: {kind!r}")

        fmt = lambda row: f"{row[0]}: {row[1]} ({row[2]:.1f}%)"

        def ask_criterion() -> str | None:
            print("\nСтатистика по критерию:")
            for key, label, _ in criteria:
                print(f"  [{key}] {label}")
            raw = input("[Enter] отмена\n> ").strip()
            if raw == "":
                return None
            for key, _, kind in criteria:
                if raw == key:
                    return kind
            print("Не понял выбор")
            return None

        kind = ask_criterion()
        if kind is None:
            print("Отменено")
            return

        def switcher():
            new_kind = ask_criterion()
            if new_kind is None:
                return None
            return make(new_kind)

        def switch_hint() -> str:
            return "сменить критерий"

        loader, formatter, header = make(kind)
        self._paginate(
            loader=loader,
            formatter=formatter,
            allow_actions=False,
            empty_message="Нет данных",
            header=header,
            switcher=switcher,
            switch_hint=switch_hint,
        )

    # ---------- экспорт ----------
    def _export(self) -> None:
        print("\nЭкспорт: [1] Отчёт (статистика)  [2] Выгрузка БД  [Enter] отмена")
        choice = input("> ").strip()
        if choice == "":
            return
        if choice == "1":
            self._export_report()
        elif choice == "2":
            self._export_db()
        else:
            print("Не понял выбор")

    def _export_report(self) -> None:
        print("Формат: [1] TXT  [2] HTML  [Enter] отмена")
        fmt = input("> ").strip()
        if fmt == "":
            return
        if fmt not in ("1", "2"):
            print("Не понял выбор")
            return

        if not self.export_dir.is_dir():
            print(f"Папка для экспорта не существует: {self.export_dir}")
            return

        total = self.service.count()
        genre_rows = self.service.stats_by_genre()
        author_rows = self.service.stats_by_author()
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if fmt == "1":
            content = report_txt(total, genre_rows, author_rows, generated_at)
            ext = "txt"
        else:
            content = report_html(total, genre_rows, author_rows, generated_at)
            ext = "html"

        path = self.export_dir / f"report_{total}_books.{ext}"
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as e:
            print(f"Ошибка записи: {e}")
            return
        print(f"Отчёт сохранён: {path} ({len(content)} байт)")

    def _export_db(self) -> None:
        print("Формат: [1] TXT  [2] HTML  [Enter] отмена")
        fmt = input("> ").strip()
        if fmt == "":
            return
        if fmt not in ("1", "2"):
            print("Не понял выбор")
            return

        if not self.export_dir.is_dir():
            print(f"Папка для экспорта не существует: {self.export_dir}")
            return

        books = self.service.list_books()
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if fmt == "1":
            content = dump_txt(books, generated_at)
            ext = "txt"
        else:
            content = dump_html(books, generated_at)
            ext = "html"

        path = self.export_dir / f"dump_{len(books)}_books.{ext}"
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as e:
            print(f"Ошибка записи: {e}")
            return
        print(f"Выгрузка сохранена: {path} ({len(content)} байт)")

    # ---------- помощники ввода ----------
    def _ask_page_size(self) -> int | None:
        print(f"Доступные размеры: {PAGE_SIZES}")
        try:
            n = int(input(f"Новый размер (Enter — оставить {self.page_size}): ").strip()
                        or str(self.page_size))
        except ValueError:
            print("Нужно число")
            return None
        if n not in PAGE_SIZES:
            print(f"Можно только {PAGE_SIZES}")
            return None
        return n

    def _ask_required(self, prompt: str, current: str | None = None) -> str:
        while True:
            suffix = f" [{current}]" if current else ""
            v = input(f"{prompt}{suffix}: ").strip()
            if v:
                return v
            if current:
                return current
            print("Поле не может быть пустым")

    def _ask_optional(self, prompt: str, current: str | None = None) -> str | None:
        suffix = f" [{current}]" if current is not None else ""
        v = input(f"{prompt}{suffix}: ").strip()
        if v == "":
            return current
        return v

    def _ask_year(self, current: int | None = None) -> int | None:
        suffix = f" [{current}]" if current is not None else ""
        while True:
            v = input(f"Год (Enter — пропустить){suffix}: ").strip()
            if v == "":
                return current
            try:
                return int(v)
            except ValueError:
                print(f"Год должен быть числом ({YEAR_MIN}..{YEAR_MAX})")

    def _format_book_full(self, book: Book) -> str:
        return (
            f"  id:        {book.id}\n"
            f"  Автор:     {book.author}\n"
            f"  Фамилия:   {book.last_name}\n"
            f"  Имя:       {book.first_name or '—'}\n"
            f"  Отчество:  {book.middle_name or '—'}\n"
            f"  Название:  {book.title}\n"
            f"  Год:       {book.year if book.year is not None else '—'}\n"
            f"  Жанр:      {book.genre or '—'}\n"
            f"  Город:     {book.city or '—'}\n"
            f"  Издание:   {book.publisher or '—'}"
        )
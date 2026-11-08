#!/usr/bin/python3
# -*- coding: utf-8 -*-
import csv
import io
import re
import sqlite3
from pathlib import Path
from typing import Optional

from book import Book


REQUIRED_HEADERS = {"Фамилия", "Название"}   # ← добавить


def validate_csv(path: str) -> tuple[bool, str]:   # ← добавить
    """Проверяет, что файл существует, читается в UTF-8 и содержит нужные колонки."""
    p = Path(path)
    if not p.exists():
        return False, f"Файл не найден: {path}"
    if not p.is_file():
        return False, f"Это не файл: {path}"
    try:
        with open(p, encoding="utf-8-sig", newline="") as f:
            text = f.read()
    except UnicodeDecodeError:
        return False, "Файл не в UTF-8 (возможно, кодировка cp1251?)"
    text = re.sub(r";\s*\r?\n", "\n", text)
    text = re.sub(r";\s*$", "", text.rstrip())
    reader = csv.reader(io.StringIO(text), skipinitialspace=True)
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        return False, "Файл пуст"
    missing = REQUIRED_HEADERS - set(header)
    if missing:
        return False, f"В заголовке нет колонок: {sorted(missing)}"
    return True, ""


class SqliteBookRepository:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function(
            "py_lower", 1, lambda s: s.casefold() if s is not None else None
        )

    def create_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                last_name   TEXT NOT NULL,
                first_name  TEXT,
                middle_name TEXT,
                title       TEXT NOT NULL,
                year        INTEGER,
                genre       TEXT,
                city        TEXT,
                publisher   TEXT
            )
        """)
        self.conn.commit()

    def drop(self) -> None:
        self.conn.execute("DROP TABLE IF EXISTS books")
        self.conn.commit()

    def import_csv(self, path: str) -> int:
        self.create_schema()
        with open(path, encoding="utf-8-sig", newline="") as f:
            text = f.read()

        # формат: поля в кавычках через ", ", запись завершается ";\n"
        text = re.sub(r";\s*\r?\n", "\n", text)
        text = re.sub(r";\s*$", "", text.rstrip())

        reader = csv.reader(io.StringIO(text), skipinitialspace=True)
        try:
            header = [h.strip() for h in next(reader)]
        except StopIteration:
            return 0

        idx = {name: header.index(name) for name in header}

        def get(row, name):
            i = idx.get(name)
            if i is None or i >= len(row):
                return ""
            return (row[i] or "").strip()

        rows = []
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            last = get(row, "Фамилия")
            title = get(row, "Название")
            if not last or not title:
                continue
            year_raw = get(row, "Год")
            try:
                year = int(year_raw) if year_raw else None
            except ValueError:
                year = None
            rows.append((
                last,
                get(row, "Имя") or None,
                get(row, "Отчество") or None,
                title,
                year,
                get(row, "Жанр") or None,
                get(row, "Город") or None,
                get(row, "Издание") or None,
            ))

        self.conn.executemany("""
            INSERT INTO books(last_name, first_name, middle_name, title, year, genre, city, publisher)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        self.conn.commit()
        return len(rows)

    def add(self, book: Book) -> int:
        cur = self.conn.execute("""
            INSERT INTO books(last_name, first_name, middle_name, title, year, genre, city, publisher)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (book.last_name, book.first_name, book.middle_name, book.title,
              book.year, book.genre, book.city, book.publisher))
        self.conn.commit()
        return cur.lastrowid

    def get(self, book_id: int) -> Optional[Book]:
        row = self.conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row_to_book(row) if row else None

    def list_all(self) -> list[Book]:
        rows = self.conn.execute(
            "SELECT * FROM books ORDER BY last_name, first_name, title"
        ).fetchall()
        return [self._row_to_book(r) for r in rows]

    # Запрос с сортировкой
    _SORT_EXPRESSIONS = {
        "author": ("last_name",),
        "title":  ("title",),
        "year":   ("year",),
        "genre":  ("genre",),
        "id":     ("id",),
    }

    def list_all_with_sort(self, sort_by: str = "author", reverse: bool = False) -> list[Book]:
        if sort_by not in self._SORT_EXPRESSIONS:
            raise ValueError(f"Неизвестный ключ сортировки: {sort_by!r}")
        columns = self._SORT_EXPRESSIONS[sort_by]
        direction = "DESC" if reverse else "ASC"

        order_parts = []
        for col in columns:
            order_parts.append(f"CASE WHEN {col} IS NULL THEN 1 ELSE 0 END ASC")
            order_parts.append(f"{col} {direction}")
        order_sql = ", ".join(order_parts)

        rows = self.conn.execute(
            f"SELECT * FROM books ORDER BY {order_sql}"
        ).fetchall()
        return [self._row_to_book(r) for r in rows]

    _ANY_TEXT_FIELDS = (
        "last_name", "first_name", "middle_name",
        "title", "genre", "city", "publisher",
    )

    def find_by_author(self, substr: str) -> list[Book]:
        pattern = f"%{substr.casefold()}%"
        rows = self.conn.execute("""
            SELECT * FROM books
            WHERE py_lower(last_name || ' ' || COALESCE(first_name, '') || ' ' || COALESCE(middle_name, '')) LIKE ?
            ORDER BY last_name, first_name, middle_name
        """, (pattern,)).fetchall()
        return [self._row_to_book(r) for r in rows]

    def find_by_title(self, substr: str) -> list[Book]:
        pattern = f"%{substr.casefold()}%"
        rows = self.conn.execute(
            "SELECT * FROM books WHERE py_lower(title) LIKE ? ORDER BY title",
            (pattern,),
        ).fetchall()
        return [self._row_to_book(r) for r in rows]

    def find_by_genre(self, substr: str) -> list[Book]:
        pattern = f"%{substr.casefold()}%"
        rows = self.conn.execute(
            "SELECT * FROM books WHERE py_lower(genre) LIKE ? ORDER BY last_name, title",
            (pattern,),
        ).fetchall()
        return [self._row_to_book(r) for r in rows]

    def find_by_year_range(self, year_from: int, year_to: int) -> list[Book]:
        rows = self.conn.execute(
            "SELECT * FROM books WHERE year BETWEEN ? AND ? ORDER BY year, last_name",
            (year_from, year_to),
        ).fetchall()
        return [self._row_to_book(r) for r in rows]

    def find_by_id(self, book_id: int) -> list[Book]:
        row = self.conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return [self._row_to_book(row)] if row else []

    def find_any(self, query: str) -> list[Book]:
        pattern = f"%{query.casefold()}%"
        or_parts = [f"py_lower({col}) LIKE ?" for col in self._ANY_TEXT_FIELDS]
        params: list = [pattern] * len(self._ANY_TEXT_FIELDS)
        try:
            num = int(query)
        except ValueError:
            num = None
        if num is not None:
            or_parts.append("year = ?")
            params.append(num)
            or_parts.append("id = ?")
            params.append(num)
        where = " OR ".join(or_parts)
        rows = self.conn.execute(
            f"SELECT * FROM books WHERE {where} ORDER BY last_name, first_name, title",
            params,
        ).fetchall()
        return [self._row_to_book(r) for r in rows]

    def update(self, book: Book) -> None:
        self.conn.execute("""
            UPDATE books
               SET last_name=?, first_name=?, middle_name=?, title=?,
                   year=?, genre=?, city=?, publisher=?
             WHERE id=?
        """, (book.last_name, book.first_name, book.middle_name, book.title,
              book.year, book.genre, book.city, book.publisher, book.id))
        self.conn.commit()

    def delete(self, book_id: int) -> None:
        self.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    def close(self) -> None:
        self.conn.close()

    def _row_to_book(self, row: sqlite3.Row) -> Book:
        return Book(
            id=row["id"],
            last_name=row["last_name"],
            first_name=row["first_name"],
            middle_name=row["middle_name"],
            title=row["title"],
            year=row["year"],
            genre=row["genre"],
            city=row["city"],
            publisher=row["publisher"],
        )

    def count_by_genre(self) -> list[tuple[str | None, int]]:
        rows = self.conn.execute("""
            SELECT genre, COUNT(*) AS cnt
            FROM books
            GROUP BY genre
            ORDER BY cnt DESC,
                     CASE WHEN genre IS NULL THEN 1 ELSE 0 END ASC,
                     genre ASC
        """).fetchall()
        return [(r["genre"], r["cnt"]) for r in rows]

    def count_by_author(self) -> list[tuple[str, int]]:
        rows = self.conn.execute("""
            SELECT RTRIM(
                       COALESCE(last_name, '') || ' ' ||
                       COALESCE(first_name, '') || ' ' ||
                       COALESCE(middle_name, '')
                   ) AS author,
                   COUNT(*) AS cnt
            FROM books
            GROUP BY author
            ORDER BY cnt DESC, author ASC
        """).fetchall()
        return [(r["author"], r["cnt"]) for r in rows]
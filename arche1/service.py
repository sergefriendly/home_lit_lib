#!/usr/bin/python3
# -*- coding: utf-8 -*-
from typing import Optional

from book import Book
from repository import SqliteBookRepository

YEAR_MIN = -3000
YEAR_MAX = 2100


class LibraryService:
    def __init__(self, repo: SqliteBookRepository):
        self.repo = repo

    def _validate(self, book: Book) -> None:
        if not book.last_name or not book.last_name.strip():
            raise ValueError("Фамилия не может быть пустой")
        if not book.title or not book.title.strip():
            raise ValueError("Название не может быть пустым")
        if book.year is not None:
            if not isinstance(book.year, int):
                raise ValueError("Год должен быть целым числом")
            if not (YEAR_MIN <= book.year <= YEAR_MAX):
                raise ValueError(
                    f"Год должен быть в диапазоне {YEAR_MIN}..{YEAR_MAX}, "
                    f"получено: {book.year}"
                )

    def add_book(self, book: Book) -> int:
        self._validate(book)
        return self.repo.add(book)

    def update_book(self, book: Book) -> None:
        if book.id is None:
            raise ValueError("Нельзя обновить книгу без id")
        self._validate(book)
        self.repo.update(book)

    def get_book(self, book_id: int) -> Optional[Book]:
        return self.repo.get(book_id)

    def list_books(self, sort_by: str | None = None, reverse: bool = False) -> list[Book]:
        if sort_by is None:
            return self.repo.list_all()
        return self.repo.list_all_with_sort(sort_by=sort_by, reverse=reverse)

    def search_by_author(self, substr: str) -> list[Book]:
        substr = (substr or "").strip()
        if not substr:
            raise ValueError("Подстрока не может быть пустой")
        return self.repo.find_by_author(substr)

    def search_by_title(self, substr: str) -> list[Book]:
        substr = (substr or "").strip()
        if not substr:
            raise ValueError("Подстрока не может быть пустой")
        return self.repo.find_by_title(substr)

    def search_by_genre(self, substr: str) -> list[Book]:
        substr = (substr or "").strip()
        if not substr:
            raise ValueError("Подстрока не может быть пустой")
        return self.repo.find_by_genre(substr)

    def search_by_year(self, year_from: int, year_to: int) -> list[Book]:
        if year_from > year_to:
            year_from, year_to = year_to, year_from
        return self.repo.find_by_year_range(year_from, year_to)

    def search_by_id(self, book_id: int) -> list[Book]:
        return self.repo.find_by_id(book_id)

    def search_any(self, query: str) -> list[Book]:
        query = (query or "").strip()
        if not query:
            raise ValueError("Строка поиска не может быть пустой")
        return self.repo.find_any(query)

    def delete_book(self, book_id: int) -> None:
        self.repo.delete(book_id)

    def import_csv(self, path: str) -> int:
        return self.repo.import_csv(path)

    def count(self) -> int:
        return self.repo.count()

    def clear_all(self) -> None:
        self.repo.drop()
        self.repo.create_schema()

    def stats_by_genre(self) -> list[tuple[str | None, int]]:
        return self.repo.count_by_genre()

    def stats_by_author(self) -> list[tuple[str, int]]:
        return self.repo.count_by_author()
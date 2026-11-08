#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from pathlib import Path

from book import Book
from repository import SqliteBookRepository
from service import LibraryService

from checks._db_helpers import new_service
from checks._helpers import mk_book


def check_add_empty_last_name():
    service, repo, tmp = new_service()
    try:
        try:
            service.add_book(mk_book(last_name=""))
        except ValueError as e:
            assert "Фамилия" in str(e), str(e)
        else:
            assert False, "ожидался ValueError на пустую фамилию"
    finally:
        repo.close()
        tmp.cleanup()


def check_add_empty_title():
    service, repo, tmp = new_service()
    try:
        try:
            service.add_book(mk_book(title="   "))
        except ValueError as e:
            assert "Название" in str(e), str(e)
        else:
            assert False, "ожидался ValueError на пустое название"
    finally:
        repo.close()
        tmp.cleanup()


def check_add_year_out_of_range():
    service, repo, tmp = new_service()
    try:
        for bad in (-5000, 3000):
            try:
                service.add_book(mk_book(year=bad))
            except ValueError as e:
                assert "диапазон" in str(e), str(e)
            else:
                assert False, f"ожидался ValueError на год {bad}"
    finally:
        repo.close()
        tmp.cleanup()


def check_add_year_none_ok():
    service, repo, tmp = new_service()
    try:
        new_id = service.add_book(mk_book(year=None))
        assert isinstance(new_id, int) and new_id > 0, new_id
        got = service.get_book(new_id)
        assert got is not None and got.year is None
    finally:
        repo.close()
        tmp.cleanup()


def check_update_without_id():
    service, repo, tmp = new_service()
    try:
        book = mk_book()          # id=None
        try:
            service.update_book(book)
        except ValueError as e:
            assert "id" in str(e), str(e)
        else:
            assert False, "ожидался ValueError на update без id"
    finally:
        repo.close()
        tmp.cleanup()


def check_service_crud_cycle():
    service, repo, tmp = new_service()
    try:
        new_id = service.add_book(mk_book(last_name="Пушкин", title="Онегин", year=1833))
        got = service.get_book(new_id)
        assert got is not None and got.title == "Онегин"

        got.year = 1837
        service.update_book(got)
        assert service.get_book(new_id).year == 1837

        service.delete_book(new_id)
        assert service.get_book(new_id) is None
    finally:
        repo.close()
        tmp.cleanup()


def check_clear_all():
    service, repo, tmp = new_service()
    try:
        service.add_book(mk_book(last_name="Пушкин", title="Онегин"))
        service.add_book(mk_book(last_name="Гомер", title="Илиада"))
        assert service.count() == 2
        service.clear_all()
        assert service.count() == 0
        # после clear_all таблица существует (create_schema) — можно добавлять снова
        new_id = service.add_book(mk_book(last_name="Толстой", title="Война и мир"))
        assert new_id is not None
        assert service.count() == 1
    finally:
        repo.close()
        tmp.cleanup()


def check_list_books_delegates():
    service, repo, tmp = new_service()
    try:
        service.add_book(mk_book(last_name="Пушкин", title="Онегин", year=1833))
        service.add_book(mk_book(last_name="Гомер", title="Илиада", year=None))
        books = service.list_books(sort_by="year")
        assert [b.year for b in books] == [1833, None], [b.year for b in books]
        books_default = service.list_books()
        assert len(books_default) == 2, len(books_default)
    finally:
        repo.close()
        tmp.cleanup()


def check_search_by_field_delegates():
    service, repo, tmp = new_service()
    try:
        service.add_book(mk_book(last_name="Пушкин", title="Онегин", year=1833))
        service.add_book(mk_book(last_name="Гомер", title="Илиада", year=None))
        assert len(service.search_by_author("пуш")) == 1
        assert len(service.search_by_title("онег")) == 1
        assert len(service.search_by_year(1833, 1833)) == 1
        try:
            service.search_by_author("")
        except ValueError as e:
            assert "пуст" in str(e).lower() or "подстрок" in str(e).lower(), str(e)
        else:
            assert False, "ожидался ValueError на пустую подстроку"
    finally:
        repo.close()
        tmp.cleanup()


def check_search_any_delegates():
    service, repo, tmp = new_service()
    try:
        service.add_book(mk_book(last_name="Пушкин", title="Онегин", year=1833))
        assert len(service.search_any("пуш")) == 1
        assert len(service.search_any("1833")) == 1
        assert service.search_any("нет-такого") == []
    finally:
        repo.close()
        tmp.cleanup()


def check_stats_delegates():
    service, repo, tmp = new_service()
    try:
        service.add_book(mk_book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                                 title="Онегин", genre="роман"))
        service.add_book(mk_book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                                 title="Руслан", genre="роман"))
        service.add_book(mk_book(last_name="Гомер", title="Илиада", genre="эпос"))
        genres = dict(service.stats_by_genre())
        assert genres.get("роман") == 2, genres
        assert genres.get("эпос") == 1, genres
        authors = dict(service.stats_by_author())
        assert authors.get("Пушкин Александр Сергеевич") == 2, authors
        assert authors.get("Гомер") == 1, authors
    finally:
        repo.close()
        tmp.cleanup()
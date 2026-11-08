#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
import re
from pathlib import Path
from book import Book
from checks._db_helpers import new_repo
from repository import validate_csv


CSV_PATH = Path(__file__).resolve().parent.parent.parent / "books.csv"


def _expected_records(path: Path) -> int:
    """Число записей в CSV = число непустых строк минус заголовок."""
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r";\s*\r?\n", "\n", text)
    text = re.sub(r";\s*$", "", text.rstrip())
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return max(0, len(lines) - 1)


def check_import_csv_count(csv_path=None):
    repo, tmp = new_repo()
    try:
        csv = Path(csv_path) if csv_path else CSV_PATH
        expected = _expected_records(csv)
        n = repo.import_csv(str(csv))
        assert n == expected, f"в файле {expected} записей, импортировано {n}"
        assert repo.count() == expected, f"count={repo.count()} != {expected}"
    finally:
        repo.close()
        tmp.cleanup()


def check_import_archimedes(csv_path=None):
    repo, tmp = new_repo()
    try:
        csv = Path(csv_path) if csv_path else CSV_PATH
        repo.import_csv(str(csv))
        books = repo.list_all()
        arch = [b for b in books if b.last_name == "Архимед"]
        assert arch, "Архимед не найден в импортированных данных"
        for b in arch:
            assert b.first_name is None, f"у Архимеда first_name={b.first_name!r}"
            assert b.middle_name is None, f"у Архимеда middle_name={b.middle_name!r}"
            assert b.author == "Архимед", repr(b.author)
    finally:
        repo.close()
        tmp.cleanup()


def check_import_empty_fields(csv_path=None):
    repo, tmp = new_repo()
    try:
        csv = Path(csv_path) if csv_path else CSV_PATH
        repo.import_csv(str(csv))
        books = repo.list_all()
        # хотя бы у одной книги должен быть None в city или publisher —
        # иначе импорт не превращает "" в None
        has_none = any(b.city is None or b.publisher is None for b in books)
        assert has_none, "ни одного None в city/publisher — импорт не превращает пустые поля в None"
    finally:
        repo.close()
        tmp.cleanup()


def check_crud_cycle():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        book = Book(
            last_name="Тестов", first_name="Тест", middle_name=None,
            title="Тестовая книга", year=2000, genre="тест",
            city=None, publisher=None,
        )
        new_id = repo.add(book)
        assert new_id is not None, "add не вернул id"

        got = repo.get(new_id)
        assert got is not None, f"get({new_id}) вернул None"
        assert got.title == "Тестовая книга"
        assert got.year == 2000
        assert got.first_name == "Тест"
        assert got.middle_name is None

        got.year = 2024
        got.genre = "обновлённый"
        repo.update(got)
        got2 = repo.get(new_id)
        assert got2.year == 2024, f"год после update: {got2.year}"
        assert got2.genre == "обновлённый"

        repo.delete(new_id)
        assert repo.get(new_id) is None, "delete не удалил запись"
    finally:
        repo.close()
        tmp.cleanup()


def check_list_all_sorted(csv_path=None):
    repo, tmp = new_repo()
    try:
        csv = Path(csv_path) if csv_path else CSV_PATH
        repo.import_csv(str(csv))
        books = repo.list_all()
        keys = [(b.last_name, b.first_name or "", b.title) for b in books]
        assert keys == sorted(keys), "list_all не отсортирован по (last_name, first_name, title)"
    finally:
        repo.close()
        tmp.cleanup()


def check_drop_recreates_empty(csv_path=None):
    repo, tmp = new_repo()
    try:
        csv = Path(csv_path) if csv_path else CSV_PATH
        repo.import_csv(str(csv))
        assert repo.count() == 98
        repo.drop()
        repo.create_schema()
        assert repo.count() == 0, f"после drop+create_schema count={repo.count()}"
    finally:
        repo.close()
        tmp.cleanup()


def check_validate_csv_ok():
    assert CSV_PATH.exists(), f"нет файла {CSV_PATH}"
    ok, err = validate_csv(str(CSV_PATH))
    assert ok is True, f"ожидался True, получено ({ok!r}, {err!r})"
    assert err == "", f"ожидалось пустое сообщение, получено {err!r}"


def check_validate_csv_not_found():
    ok, err = validate_csv("/tmp/нет-такого-файла-12345.csv")
    assert ok is False
    assert "не найден" in err, err


def check_validate_csv_not_a_file():
    # передаём папку вместо файла
    ok, err = validate_csv("/tmp")
    assert ok is False
    assert "не файл" in err, err


def check_validate_csv_empty_file():
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    try:
        tmp.close()
        ok, err = validate_csv(tmp.name)
        assert ok is False
        assert "пуст" in err, err
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def check_validate_csv_missing_headers():
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    try:
        tmp.write('"Автор", "Книга";\n"Пушкин", "Онегин";\n')
        tmp.close()
        ok, err = validate_csv(tmp.name)
        assert ok is False
        assert "Фамилия" in err or "Название" in err, err
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def check_validate_csv_bad_encoding():
    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False)
    try:
        # cp1251-байты, которые невалидны в UTF-8
        tmp.write("Фамилия,Название\nПушкин,Онегин\n".encode("cp1251"))
        tmp.close()
        ok, err = validate_csv(tmp.name)
        assert ok is False
        assert "UTF-8" in err or "кодировк" in err.lower(), err
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def check_list_all_with_sort_author():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                      title="Онегин", year=1833, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="Гомер", first_name=None, middle_name=None,
                      title="Илиада", year=None, genre="эпос", city=None, publisher=None))
        repo.add(Book(last_name="Архимед", first_name=None, middle_name=None,
                      title="Сочинения", year=None, genre="трактат", city=None, publisher=None))
        books = repo.list_all_with_sort(sort_by="author")
        last_names = [b.last_name for b in books]
        assert last_names == sorted(last_names, key=lambda s: s.casefold()), last_names
    finally:
        repo.close()
        tmp.cleanup()


def check_list_all_with_sort_year_none_last():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="A", first_name=None, middle_name=None,
                      title="a", year=2000, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="B", first_name=None, middle_name=None,
                      title="b", year=None, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="C", first_name=None, middle_name=None,
                      title="c", year=1900, genre=None, city=None, publisher=None))
        asc = [b.year for b in repo.list_all_with_sort(sort_by="year")]
        assert asc == [1900, 2000, None], asc
        desc = [b.year for b in repo.list_all_with_sort(sort_by="year", reverse=True)]
        assert desc == [2000, 1900, None], desc
    finally:
        repo.close()
        tmp.cleanup()


def check_list_all_with_sort_unknown_key():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        try:
            repo.list_all_with_sort(sort_by="years")
        except ValueError as e:
            assert "сортиров" in str(e).lower() or "sort" in str(e).lower(), str(e)
        else:
            assert False, "ожидался ValueError на неизвестный ключ"
    finally:
        repo.close()
        tmp.cleanup()

def check_find_by_author_substr():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                      title="Онегин", year=1833, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="Гомер", first_name=None, middle_name=None,
                      title="Илиада", year=None, genre="эпос", city=None, publisher=None))
        books = repo.find_by_author("пуш")
        assert len(books) == 1 and books[0].last_name == "Пушкин", [b.last_name for b in books]
        books = repo.find_by_author("александр")   # по имени в склейке
        assert len(books) == 1 and books[0].last_name == "Пушкин"
        books = repo.find_by_author("ПУШ")         # регистронезависимо
        assert len(books) == 1
    finally:
        repo.close()
        tmp.cleanup()


def check_find_by_title_substr():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="Пушкин", first_name=None, middle_name=None,
                      title="Евгений Онегин", year=None, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="Гомер", first_name=None, middle_name=None,
                      title="Илиада", year=None, genre=None, city=None, publisher=None))
        books = repo.find_by_title("онег")
        assert len(books) == 1 and books[0].title == "Евгений Онегин"
    finally:
        repo.close()
        tmp.cleanup()


def check_find_by_genre_substr():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="A", first_name=None, middle_name=None,
                      title="a", year=None, genre="роман", city=None, publisher=None))
        repo.add(Book(last_name="B", first_name=None, middle_name=None,
                      title="b", year=None, genre="эпос", city=None, publisher=None))
        books = repo.find_by_genre("ром")
        assert len(books) == 1 and books[0].genre == "роман"
    finally:
        repo.close()
        tmp.cleanup()


def check_find_by_year_exact():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="A", first_name=None, middle_name=None,
                      title="a", year=1833, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="B", first_name=None, middle_name=None,
                      title="b", year=1900, genre=None, city=None, publisher=None))
        books = repo.find_by_year_range(1833, 1833)
        assert len(books) == 1 and books[0].year == 1833
    finally:
        repo.close()
        tmp.cleanup()


def check_find_by_year_range():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="A", first_name=None, middle_name=None,
                      title="a", year=1800, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="B", first_name=None, middle_name=None,
                      title="b", year=1850, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="C", first_name=None, middle_name=None,
                      title="c", year=1900, genre=None, city=None, publisher=None))
        books = repo.find_by_year_range(1800, 1850)
        assert [b.year for b in books] == [1800, 1850], [b.year for b in books]
    finally:
        repo.close()
        tmp.cleanup()


def check_find_by_id():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        new_id = repo.add(Book(last_name="A", first_name=None, middle_name=None,
                               title="a", year=None, genre=None, city=None, publisher=None))
        books = repo.find_by_id(new_id)
        assert len(books) == 1 and books[0].id == new_id
        assert repo.find_by_id(9999) == []
    finally:
        repo.close()
        tmp.cleanup()


def check_find_any_text():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="Пушкин", first_name=None, middle_name=None,
                      title="Онегин", year=1833, genre=None, city="Москва", publisher=None))
        repo.add(Book(last_name="Гомер", first_name=None, middle_name=None,
                      title="Илиада", year=None, genre="эпос", city=None, publisher=None))
        books = repo.find_any("пуш")          # по last_name
        assert len(books) == 1
        books = repo.find_any("онег")         # по title
        assert len(books) == 1
        books = repo.find_any("моск")         # по city
        assert len(books) == 1
    finally:
        repo.close()
        tmp.cleanup()


def check_find_any_numeric():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="A", first_name=None, middle_name=None,
                      title="a", year=1833, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="B", first_name=None, middle_name=None,
                      title="b", year=1900, genre=None, city=None, publisher=None))
        books = repo.find_any("1833")         # year = 1833
        assert len(books) == 1 and books[0].year == 1833
        assert repo.find_any("99999") == []   # ни year, ни id, ни текст
    finally:
        repo.close()
        tmp.cleanup()


def check_count_by_genre():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="A", first_name=None, middle_name=None,
                      title="a1", year=None, genre="роман", city=None, publisher=None))
        repo.add(Book(last_name="B", first_name=None, middle_name=None,
                      title="b1", year=None, genre="роман", city=None, publisher=None))
        repo.add(Book(last_name="C", first_name=None, middle_name=None,
                      title="c1", year=None, genre="эпос", city=None, publisher=None))
        repo.add(Book(last_name="D", first_name=None, middle_name=None,
                      title="d1", year=None, genre=None, city=None, publisher=None))
        rows = repo.count_by_genre()
        assert len(rows) == 3, rows
        assert rows[0] == ("роман", 2), rows
        assert rows[-1][0] is None, rows           # NULL в конце
        assert dict(rows).get(None) == 1, rows
    finally:
        repo.close()
        tmp.cleanup()


def check_count_by_author():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        repo.add(Book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                      title="Онегин", year=None, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                      title="Руслан", year=None, genre=None, city=None, publisher=None))
        repo.add(Book(last_name="Гомер", first_name=None, middle_name=None,
                      title="Илиада", year=None, genre=None, city=None, publisher=None))
        rows = repo.count_by_author()
        authors = dict(rows)
        assert len(rows) == 2, rows
        assert authors.get("Пушкин Александр Сергеевич") == 2, authors
        assert authors.get("Гомер") == 1, authors
        for author, _ in rows:
            assert author == author.rstrip(), repr(author)   # нет хвостовых пробелов
    finally:
        repo.close()
        tmp.cleanup()


def check_count_empty_base():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        assert repo.count_by_genre() == [], repo.count_by_genre()
        assert repo.count_by_author() == [], repo.count_by_author()
    finally:
        repo.close()
        tmp.cleanup()


def check_list_all_with_sort_id():
    repo, tmp = new_repo()
    try:
        repo.create_schema()
        id_a = repo.add(Book(last_name="Пушкин", first_name=None, middle_name=None,
                             title="Онегин", year=None, genre=None, city=None, publisher=None))
        id_b = repo.add(Book(last_name="Гомер", first_name=None, middle_name=None,
                             title="Илиада", year=None, genre=None, city=None, publisher=None))
        id_c = repo.add(Book(last_name="Архимед", first_name=None, middle_name=None,
                             title="Сочинения", year=None, genre=None, city=None, publisher=None))
        asc = [b.id for b in repo.list_all_with_sort(sort_by="id")]
        assert asc == [id_a, id_b, id_c], asc
        desc = [b.id for b in repo.list_all_with_sort(sort_by="id", reverse=True)]
        assert desc == [id_c, id_b, id_a], desc
    finally:
        repo.close()
        tmp.cleanup()
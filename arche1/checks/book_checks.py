#!/usr/bin/python3
# -*- coding: utf-8 -*-
from checks._helpers import mk_book


def check_author_three_parts():
    b = mk_book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич")
    assert b.author == "Пушкин Александр Сергеевич", b.author


def check_author_two_parts():
    b = mk_book(last_name="Толстой", first_name="Лев")
    assert b.author == "Толстой Лев", repr(b.author)


def check_author_single_word():
    b = mk_book(last_name="Архимед")
    assert b.author == "Архимед", repr(b.author)


def check_author_no_double_spaces():
    b = mk_book(last_name="Гомер")
    assert "  " not in b.author, repr(b.author)


def check_author_with_empty_string_not_none():
    b = mk_book(last_name="Гомер", first_name="", middle_name="")
    assert b.author == "Гомер", repr(b.author)


def check_str_with_year():
    b = mk_book(last_name="Пушкин", first_name="Александр", middle_name="Сергеевич",
                title="Евгений Онегин", year=1833, id=1)
    s = str(b)
    assert "[1]" in s and "Пушкин Александр Сергеевич" in s
    assert "Евгений Онегин" in s and "(1833)" in s, s


def check_str_without_year():
    b = mk_book(last_name="Гомер", title="Илиада", year=None, id=2)
    s = str(b)
    assert "(—)" in s, s
    assert "None" not in s, s


def check_equality():
    a = mk_book(last_name="Пушкин", title="Онегин", year=1833)
    b = mk_book(last_name="Пушкин", title="Онегин", year=1833)
    c = mk_book(last_name="Пушкин", title="Онегин", year=1837)
    assert a == b
    assert a != c


def check_id_default_is_none():
    b = mk_book()
    assert b.id is None, b.id


def check_str_with_genre():
    b = mk_book(last_name="Гомер", title="Илиада", year=None, genre="эпос", id=3)
    s = str(b)
    assert "(эпос)" in s, s


def check_str_with_year_and_genre():
    b = mk_book(last_name="Пушкин", title="Онегин", year=1833, genre="роман", id=4)
    s = str(b)
    assert "(1833, роман)" in s, s
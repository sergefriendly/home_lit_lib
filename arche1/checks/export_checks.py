#!/usr/bin/python3
# -*- coding: utf-8 -*-
from checks._helpers import mk_book

from export import report_txt, report_html, dump_txt, dump_html


def check_report_txt_sections():
    txt = report_txt(2, [("роман", 2)], [("Пушкин", 2)], "2026-10-31 14:32")
    assert "Домашняя библиотека" in txt, txt
    assert "Сформирован: 2026-10-31 14:32" in txt
    assert "Всего книг: 2" in txt
    assert "По жанрам" in txt
    assert "По авторам" in txt
    assert "роман: 2 (100.0%)" in txt, txt
    assert "Пушкин: 2 (100.0%)" in txt, txt


def check_report_txt_none_genre():
    txt = report_txt(1, [(None, 1)], [("Гомер", 1)], "x")
    assert "(без жанра): 1 (100.0%)" in txt, txt


def check_report_html_structure():
    s = report_html(2, [("роман", 2)], [("Пушкин", 2)], "x")
    assert s.startswith("<!DOCTYPE html>"), s[:30]
    assert '<meta charset="utf-8">' in s
    assert "<table>" in s
    assert "<th>Жанр</th>" in s
    assert "<th>Автор</th>" in s
    assert "роман" in s
    assert "100.0%" in s


def check_report_html_escapes():
    s = report_html(1, [("<b>", 1)], [("A&B", 1)], "x")
    assert "&lt;b&gt;" in s, s
    assert "A&amp;B" in s, s
    assert "<b>" not in s, s


def check_report_empty():
    txt = report_txt(0, [], [], "x")
    assert "Всего книг: 0" in txt
    assert "(нет данных)" in txt
    h = report_html(0, [], [], "x")
    assert "всего книг: 0" in h          # ← строчная «в», как в HTML-шаблоне
    assert "(нет данных)" in h
    assert "0.0%" not in h


def check_dump_txt_contains_books():
    books = [mk_book(id=1, last_name="Пушкин", title="Онегин", year=1833),
             mk_book(id=2, last_name="Гомер", title="Илиада")]
    s = dump_txt(books, "2026-10-31 14:32")
    assert "Домашняя библиотека" in s
    assert "Всего книг: 2" in s
    assert "Пушкин" in s and "Онегин" in s and "1833" in s, s
    assert "Гомер" in s and "Илиада" in s, s
    assert "—" in s   # None → «—»


def check_dump_html_structure_and_escape():
    b = mk_book(title="<b>Онегин</b>", last_name="A&B")
    s = dump_html([b], "x")
    assert s.startswith("<!DOCTYPE html>")
    assert "<table>" in s
    assert "<th>id</th>" in s and "<th>Название</th>" in s
    assert "&lt;b&gt;Онегин&lt;/b&gt;" in s, s
    assert "A&amp;B" in s, s
    assert "<b>Онегин</b>" not in s, s
    assert "Домашняя библиотека" in s


def check_dump_empty():
    for fn, name in [(dump_txt, "txt"), (dump_html, "html")]:
        s = fn([], "x")
        assert s, f"{name}: пустой результат"
    assert "Всего книг: 0" in dump_txt([], "x")
    assert "(нет книг)" in dump_html([], "x")
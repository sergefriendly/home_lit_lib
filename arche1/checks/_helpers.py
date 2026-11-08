#!/usr/bin/python3
# -*- coding: utf-8 -*-
from book import Book


def mk_book(**kwargs) -> Book:
    defaults = dict(
        last_name="Тестов",
        first_name=None,
        middle_name=None,
        title="Книга",
        year=None,
        genre=None,
        city=None,
        publisher=None,
    )
    defaults.update(kwargs)
    return Book(**defaults)
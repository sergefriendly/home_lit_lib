#!/usr/bin/python3
# -*- coding: utf-8 -*-
from cli import ConsoleUI


def check_parse_id_single():
    assert ConsoleUI._parse_id_spec("5") == [5]


def check_parse_id_list():
    assert ConsoleUI._parse_id_spec("1, 5, 10") == [1, 5, 10]


def check_parse_id_range():
    assert ConsoleUI._parse_id_spec("10-13") == [10, 11, 12, 13]


def check_parse_id_mixed():
    assert ConsoleUI._parse_id_spec("1, 5, 10-12") == [1, 5, 10, 11, 12]


def check_parse_id_reversed_range():
    assert ConsoleUI._parse_id_spec("13-10") == [10, 11, 12, 13]


def check_parse_id_skips_invalid():
    assert ConsoleUI._parse_id_spec("1, abc, 3") == [1, 3]


def check_parse_id_empty():
    assert ConsoleUI._parse_id_spec("") == []
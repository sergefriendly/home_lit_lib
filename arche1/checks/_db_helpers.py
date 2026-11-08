#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from pathlib import Path

from repository import SqliteBookRepository
from service import LibraryService


def new_repo():
    """Временная база + репозиторий. Схему не создаёт — это делают проверки по необходимости."""
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "checks.db"
    repo = SqliteBookRepository(str(db_path))
    return repo, tmp


def new_service():
    """Временная база + репозиторий со схемой + сервис."""
    repo, tmp = new_repo()
    repo.create_schema()
    service = LibraryService(repo)
    return service, repo, tmp

#!/usr/bin/python3
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional


@dataclass
class Book:
    last_name: str
    first_name: Optional[str]
    middle_name: Optional[str]
    title: str
    year: Optional[int]
    genre: Optional[str]
    city: Optional[str]
    publisher: Optional[str]
    id: Optional[int] = None

    @property
    def author(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    """
    def __str__(self) -> str:
        year = self.year if self.year is not None else "—"
        return f"[{self.id}] {self.author} — {self.title} ({year})"
    """

    def __str__(self) -> str:
        parts = []
        if self.year is not None:
            parts.append(str(self.year))
        if self.genre:
            parts.append(self.genre)
        meta = ", ".join(parts) if parts else "—"
        return f"[{self.id}] {self.author} — {self.title} ({meta})"
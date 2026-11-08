#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import load_config, resolve_env, resolve_web
from export import dump_html, dump_txt, report_html, report_txt
from book import Book
from repository import SqliteBookRepository
from service import LibraryService

ARCH_DIR = Path(__file__).resolve().parent
BASE_DIR = ARCH_DIR.parent
TEMPLATES_DIR = ARCH_DIR / "templates"
STATIC_DIR = ARCH_DIR / "static"

CFG = load_config(BASE_DIR / "config.ini")
ENV = resolve_env(os.getenv("LIBRARY_ENV"), CFG)
DB_PATHS = {
    "dev":  BASE_DIR / "library_dev.db",
    "test": BASE_DIR / "library_test.db",
    "prod": BASE_DIR / "library_prod.db",
}
DB_PATH = DB_PATHS[ENV]
PAGE_SIZES = (15, 30, 50, 100)

app = FastAPI(title="Домашняя библиотека")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_service():
    """Открывает репозиторий на один запрос, закрывает после ответа."""
    repo = SqliteBookRepository(str(DB_PATH))
    try:
        repo.create_schema()
        yield LibraryService(repo)
    finally:
        repo.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, service: LibraryService = Depends(get_service)):
    total = service.count()
    genres = service.stats_by_genre()[:5] if total else []
    authors = service.stats_by_author()[:5] if total else []
    return templates.TemplateResponse(request, "index.html", {
        "active": "home",
        "env": ENV,
        "db_name": DB_PATH.name,
        "total": total,
        "genres": genres,
        "authors": authors,
    })


@app.get("/books", response_class=HTMLResponse)
def books_list(request: Request,
               sort: str = "author",
               reverse: int = 0,
               page: int = 1,
               size: int = 0,
               service: LibraryService = Depends(get_service)):
    page_size = size if size in PAGE_SIZES else CFG["page_size"]
    try:
        items = service.list_books(sort_by=sort, reverse=bool(reverse))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    chunk = items[start:start + page_size]
    return templates.TemplateResponse(request, "books.html", {
        "active": "books",
        "books": chunk,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "page_size": page_size,
        "sort": sort,
        "reverse": reverse,
        "page_sizes": PAGE_SIZES,
    })


# Перенесен выше, тобы не конфликотовать с /books/{book_id}
@app.get("/books/new", response_class=HTMLResponse)
def book_new_form(request: Request, back: str = "/books"):
    return templates.TemplateResponse(request, "book_form.html", {
        "active": "books",
        "mode": "add",
        "book": None,
        "error": None,
        "form": {},
        "back": back,
    })


@app.get("/books/{book_id}", response_class=HTMLResponse)
def book_detail(request: Request, book_id: int, back: str = "/books",
                service: LibraryService = Depends(get_service)):
    book = service.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Книга с id={book_id} не найдена")
    return templates.TemplateResponse(request, "book.html", {
        "active": "books",
        "book": book,
        "back": back,
    })


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, field: str = "any", q: str = "",
           page: int = 1, size: int = 0,
           service: LibraryService = Depends(get_service)):
    page_size = size if size in PAGE_SIZES else CFG["page_size"]
    results = []
    error = None
    total = 0
    total_pages = 1
    chunk = []

    if q.strip():
        try:
            if field == "author":
                results = service.search_by_author(q)
            elif field == "title":
                results = service.search_by_title(q)
            elif field == "genre":
                results = service.search_by_genre(q)
            elif field == "year":
                if "-" in q:
                    a, b = q.split("-", 1)
                    results = service.search_by_year(int(a), int(b))
                else:
                    y = int(q)
                    results = service.search_by_year(y, y)
            elif field == "id":
                results = service.search_by_id(int(q))
            else:
                results = service.search_any(q)
        except ValueError as e:
            error = str(e)

        total = len(results)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        chunk = results[start:start + page_size]

    return templates.TemplateResponse(request, "search.html", {
        "active": "search",
        "field": field,
        "q": q,
        "results": chunk,
        "total": total,
        "error": error,
        "page": page,
        "total_pages": total_pages,
        "page_size": page_size,
        "page_sizes": PAGE_SIZES,
    })


@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request, kind: str = "genre",
          service: LibraryService = Depends(get_service)):
    if kind not in ("genre", "author"):
        kind = "genre"
    total = service.count()
    if kind == "genre":
        raw = service.stats_by_genre()
        rows = [(g if g else "(без жанра)", c,
                 (c / total * 100) if total else 0.0) for g, c in raw]
    else:
        raw = service.stats_by_author()
        rows = [(a, c, (c / total * 100) if total else 0.0) for a, c in raw]
    return templates.TemplateResponse(request, "stats.html", {
        "active": "stats",
        "kind": kind,
        "total": total,
        "rows": rows,
    })


@app.get("/report", response_class=HTMLResponse)
def report(service: LibraryService = Depends(get_service)):
    return HTMLResponse(report_html(
        service.count(),
        service.stats_by_genre(),
        service.stats_by_author(),
        _now(),
    ))


@app.get("/report/download", response_class=HTMLResponse)
def report_download(service: LibraryService = Depends(get_service)):
    total = service.count()
    content = report_html(
        total,
        service.stats_by_genre(),
        service.stats_by_author(),
        _now(),
    )
    filename = f"report_{total}_books.html"
    return HTMLResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/report.txt", response_class=PlainTextResponse)
def report_txt_download(service: LibraryService = Depends(get_service)):
    total = service.count()
    content = report_txt(
        total,
        service.stats_by_genre(),
        service.stats_by_author(),
        _now(),
    )
    filename = f"report_{total}_books.txt"
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/dump", response_class=HTMLResponse)
def dump(service: LibraryService = Depends(get_service)):
    books = service.list_books()
    content = dump_html(books, _now())
    filename = f"dump_{len(books)}_books.html"
    return HTMLResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/dump.txt", response_class=PlainTextResponse)
def dump_txt_download(service: LibraryService = Depends(get_service)):
    books = service.list_books()
    content = dump_txt(books, _now())
    filename = f"dump_{len(books)}_books.txt"
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------- CRUD ----------

def _parse_year(raw: str) -> int | None:
    """Пустая строка → None; нечисло → ValueError (ловим в маршруте)."""
    raw = raw.strip()
    if not raw:
        return None
    return int(raw)


@app.post("/books")
def book_create(
    request: Request,
    back: str = "/books",
    last_name: str = Form(""),
    first_name: str = Form(""),
    middle_name: str = Form(""),
    title: str = Form(""),
    year: str = Form(""),
    genre: str = Form(""),
    city: str = Form(""),
    publisher: str = Form(""),
    service: LibraryService = Depends(get_service),
):
    form = {
        "last_name": last_name.strip(),
        "first_name": first_name.strip(),
        "middle_name": middle_name.strip(),
        "title": title.strip(),
        "year": year.strip(),
        "genre": genre.strip(),
        "city": city.strip(),
        "publisher": publisher.strip(),
    }
    try:
        year_value = _parse_year(form["year"])
        book = Book(
            last_name=form["last_name"],
            first_name=form["first_name"] or None,
            middle_name=form["middle_name"] or None,
            title=form["title"],
            year=year_value,
            genre=form["genre"] or None,
            city=form["city"] or None,
            publisher=form["publisher"] or None,
        )
        new_id = service.add_book(book)
    except (ValueError, TypeError) as e:
        return templates.TemplateResponse(request, "book_form.html", {
            "active": "books",
            "mode": "add",
            "book": None,
            "error": str(e) if str(e) else "Год должен быть числом",
            "form": form,
            "back": back,
        })
    return RedirectResponse(
        url=f"/books/{new_id}?{urlencode({'back': back})}",
        status_code=303,
    )


@app.get("/books/{book_id}/edit", response_class=HTMLResponse)
def book_edit_form(request: Request, book_id: int, back: str = "/books",
                   service: LibraryService = Depends(get_service)):
    book = service.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Книга с id={book_id} не найдена")
    return templates.TemplateResponse(request, "book_form.html", {
        "active": "books",
        "mode": "edit",
        "book": book,
        "error": None,
        "form": {},
        "back": back,
    })


@app.post("/books/{book_id}/edit")
def book_update(
    request: Request,
    book_id: int,
    back: str = "/books",
    last_name: str = Form(""),
    first_name: str = Form(""),
    middle_name: str = Form(""),
    title: str = Form(""),
    year: str = Form(""),
    genre: str = Form(""),
    city: str = Form(""),
    publisher: str = Form(""),
    service: LibraryService = Depends(get_service),
):
    existing = service.get_book(book_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Книга с id={book_id} не найдена")

    form = {
        "last_name": last_name.strip(),
        "first_name": first_name.strip(),
        "middle_name": middle_name.strip(),
        "title": title.strip(),
        "year": year.strip(),
        "genre": genre.strip(),
        "city": city.strip(),
        "publisher": publisher.strip(),
    }
    try:
        year_value = _parse_year(form["year"])
        existing.last_name = form["last_name"]
        existing.first_name = form["first_name"] or None
        existing.middle_name = form["middle_name"] or None
        existing.title = form["title"]
        existing.year = year_value
        existing.genre = form["genre"] or None
        existing.city = form["city"] or None
        existing.publisher = form["publisher"] or None
        service.update_book(existing)
    except (ValueError, TypeError) as e:
        return templates.TemplateResponse(request, "book_form.html", {
            "active": "books",
            "mode": "edit",
            "book": existing,
            "error": str(e) if str(e) else "Год должен быть числом",
            "form": form,
            "back": back,
        })
    return RedirectResponse(
        url=f"/books/{book_id}?{urlencode({'back': back})}",
        status_code=303,
    )


@app.post("/books/{book_id}/delete")
def book_delete(book_id: int, back: str = "/books",
                service: LibraryService = Depends(get_service)):
    book = service.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Книга с id={book_id} не найдена")
    service.delete_book(book_id)
    return RedirectResponse(url=back, status_code=303)


if __name__ == "__main__":
    host, port = resolve_web(os.getenv("WEB_HOST"), os.getenv("WEB_PORT"), CFG)
    print(f"ENV = {ENV}, БД = {DB_PATH.name}")
    print(f"Веб: http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port, reload=False)
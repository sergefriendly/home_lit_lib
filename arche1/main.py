import os
from pathlib import Path

from cli import ConsoleUI
from config import load_config, resolve_env
from repository import SqliteBookRepository
from service import LibraryService

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATHS = {
    "dev":  BASE_DIR / "library_dev.db",
    "test": BASE_DIR / "library_test.db",
    "prod": BASE_DIR / "library_prod.db",
}


def main() -> None:
    cfg = load_config(BASE_DIR / "config.ini")
    ENV = resolve_env(os.getenv("LIBRARY_ENV"), cfg)
    DB_PATH = DB_PATHS[ENV]
    CSV_PATH = BASE_DIR / cfg["csv_path"]

    repo = SqliteBookRepository(str(DB_PATH))
    try:
        repo.create_schema()
        service = LibraryService(repo)
        print(f"ENV = {ENV}, БД = {DB_PATH.name}, записей в базе: {service.count()}")
        ConsoleUI(
            service,
            csv_path=CSV_PATH,
            page_size=cfg["page_size"],
            export_dir=cfg["export_dir"],
        ).run()
    finally:
        repo.close()


if __name__ == "__main__":
    main()
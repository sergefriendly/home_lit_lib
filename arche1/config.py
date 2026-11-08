#!/usr/bin/python3
# -*- coding: utf-8 -*-
from configparser import ConfigParser
from pathlib import Path

VALID_ENVS = ("dev", "test", "prod")
VALID_PAGE_SIZES = (15, 30, 50, 100)

DEFAULTS = {
    "env": "dev",
    "page_size": 30,
    "csv_path": "books.csv",
    "export_dir": None,
    "web_host": "127.0.0.1",
    "web_port": 8001,
}


def load_config(path: Path) -> dict:
    """Читает INI. Возвращает {'env': str, 'page_size': int,
    'csv_path': str, 'export_dir': Path}. ValueError — если что-то не так."""
    cfg = dict(DEFAULTS)
    parser = ConfigParser()

    if path.exists():
        parser.read(path, encoding="utf-8")
        if parser.has_section("app") and parser.has_option("app", "env"):
            cfg["env"] = parser.get("app", "env").strip()
        if parser.has_section("ui") and parser.has_option("ui", "page_size"):
            raw = parser.get("ui", "page_size").strip()
            try:
                cfg["page_size"] = int(raw)
            except ValueError:
                raise ValueError(f"page_size должен быть числом, получено: {raw!r}")
        if parser.has_section("data") and parser.has_option("data", "csv_path"):
            cfg["csv_path"] = parser.get("data", "csv_path").strip()
        if parser.has_section("export") and parser.has_option("export", "export_dir"):
            raw = parser.get("export", "export_dir").strip()
            if raw:
                cfg["export_dir"] = Path(raw).expanduser()

        if parser.has_section("web"):
            if parser.has_option("web", "host"):
                cfg["web_host"] = parser.get("web", "host").strip() or "127.0.0.1"
            if parser.has_option("web", "port"):
                raw = parser.get("web", "port").strip()
                try:
                    cfg["web_port"] = int(raw)
                except ValueError:
                    raise ValueError(f"web.port должен быть числом, получено: {raw!r}")

    if cfg["env"] not in VALID_ENVS:
        raise ValueError(f"env должен быть одним из {VALID_ENVS}, получено: {cfg['env']!r}")
    if cfg["page_size"] not in VALID_PAGE_SIZES:
        raise ValueError(
            f"page_size должен быть одним из {VALID_PAGE_SIZES}, получено: {cfg['page_size']}"
        )
    if not cfg["csv_path"]:
        raise ValueError("csv_path не может быть пустым")
    if cfg["export_dir"] is None:
        raise ValueError("export_dir не задан в конфиге (секция [export])")
    if not cfg["export_dir"].is_dir():
        raise ValueError(f"export_dir не существует или не директория: {cfg['export_dir']}")

    if not cfg["web_host"]:
        raise ValueError("web.host не может быть пустым")
    if not (1 <= cfg["web_port"] <= 65535):
        raise ValueError(f"web.port должен быть в 1..65535, получено: {cfg['web_port']}")

    return cfg


def resolve_env(cli_env: str | None, file_cfg: dict) -> str:
    """Приоритет: LIBRARY_ENV (если непустой) > file_cfg['env'] > 'dev'."""
    env = cli_env.strip() if (cli_env and cli_env.strip()) else file_cfg["env"]
    if env not in VALID_ENVS:
        raise ValueError(f"env должен быть одним из {VALID_ENVS}, получено: {env!r}")
    return env


def resolve_web(env_host: str | None, env_port: str | None, file_cfg: dict) -> tuple[str, int]:
    """Приоритет: WEB_HOST/WEB_PORT (env) > config.ini [web] > дефолты.
    Пустая строка в env не считается заданной."""
    host = (env_host.strip() if env_host and env_host.strip() else file_cfg["web_host"])
    raw_port = env_port.strip() if (env_port and env_port.strip()) else str(file_cfg["web_port"])
    try:
        port = int(raw_port)
    except ValueError:
        raise ValueError(f"WEB_PORT должен быть числом, получено: {raw_port!r}")
    if not (1 <= port <= 65535):
        raise ValueError(f"WEB_PORT должен быть в 1..65535, получено: {port}")
    if not host:
        raise ValueError("WEB_HOST не может быть пустым")
    return host, port
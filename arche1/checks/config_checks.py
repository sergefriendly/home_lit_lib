#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from pathlib import Path

from config import load_config, resolve_env, DEFAULTS, resolve_web


def _write_cfg(text: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ini", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(text)
        tmp.close()
        return Path(tmp.name)
    except Exception:
        tmp.close()
        raise


def check_load_config_missing_file():
    try:
        load_config(Path("/tmp/нет-такого-конфига-12345.ini"))
    except ValueError as e:
        assert "export_dir" in str(e), str(e)
    else:
        assert False, "ожидался ValueError (export_dir обязателен)"


def check_load_config_valid():
    p = _write_cfg("""
[app]
env = test
[ui]
page_size = 50
[data]
csv_path = books.csv
[export]
export_dir = /tmp
""")
    try:
        cfg = load_config(p)
        assert cfg["env"] == "test", cfg
        assert cfg["page_size"] == 50, cfg
        assert cfg["csv_path"] == "books.csv", cfg
        assert cfg["export_dir"] == Path("/tmp"), cfg
    finally:
        p.unlink(missing_ok=True)


def check_load_config_bad_env():
    p = _write_cfg("[app]\nenv = prodd\n[export]\nexport_dir = /tmp\n")
    try:
        try:
            load_config(p)
        except ValueError as e:
            assert "env" in str(e), str(e)
        else:
            assert False, "ожидался ValueError на env=prodd"
    finally:
        p.unlink(missing_ok=True)


def check_load_config_bad_page_size():
    p = _write_cfg("[ui]\npage_size = 25\n[export]\nexport_dir = /tmp\n")
    try:
        try:
            load_config(p)
        except ValueError as e:
            assert "page_size" in str(e), str(e)
        else:
            assert False, "ожидался ValueError на page_size=25"
    finally:
        p.unlink(missing_ok=True)


def check_load_config_missing_export_dir():
    p = _write_cfg("[app]\nenv = dev\n")
    try:
        try:
            load_config(p)
        except ValueError as e:
            assert "export_dir" in str(e), str(e)
        else:
            assert False, "ожидался ValueError (export_dir не задан)"
    finally:
        p.unlink(missing_ok=True)


def check_load_config_nonexistent_export_dir():
    p = _write_cfg("[export]\nexport_dir = /tmp/нет-такой-папки-12345\n")
    try:
        try:
            load_config(p)
        except ValueError as e:
            assert "export_dir" in str(e), str(e)
        else:
            assert False, "ожидался ValueError (export_dir не существует)"
    finally:
        p.unlink(missing_ok=True)


def check_resolve_env_cli_wins():
    assert resolve_env("prod", {"env": "test"}) == "prod"


def check_resolve_env_file():
    assert resolve_env(None, {"env": "test"}) == "test"
    assert resolve_env("", {"env": "test"}) == "test"


def check_resolve_env_bad_cli():
    try:
        resolve_env("prodd", {"env": "dev"})
    except ValueError as e:
        assert "env" in str(e), str(e)
    else:
        assert False, "ожидался ValueError на env=prodd"


def check_load_config_web_defaults():
    # без секции [web] — дефолты
    p = _write_cfg("[export]\nexport_dir = /tmp\n")
    try:
        cfg = load_config(p)
        assert cfg["web_host"] == "127.0.0.1", cfg
        assert cfg["web_port"] == 8001, cfg
    finally:
        p.unlink(missing_ok=True)


def check_load_config_web_from_file():
    p = _write_cfg(
        "[export]\nexport_dir = /tmp\n"
        "[web]\nhost = 0.0.0.0\nport = 9000\n"
    )
    try:
        cfg = load_config(p)
        assert cfg["web_host"] == "0.0.0.0", cfg
        assert cfg["web_port"] == 9000, cfg
    finally:
        p.unlink(missing_ok=True)


def check_load_config_web_bad_port():
    p = _write_cfg("[export]\nexport_dir = /tmp\n[web]\nport = 99999\n")
    try:
        try:
            load_config(p)
        except ValueError as e:
            assert "web" in str(e).lower() or "port" in str(e).lower(), str(e)
        else:
            assert False, "ожидался ValueError на port=99999"
    finally:
        p.unlink(missing_ok=True)


def check_resolve_web_priority():
    file_cfg = {"web_host": "127.0.0.1", "web_port": 8001}
    # без env — из файла
    assert resolve_web(None, None, file_cfg) == ("127.0.0.1", 8001)
    # env host перекрывает
    assert resolve_web("0.0.0.0", None, file_cfg) == ("0.0.0.0", 8001)
    # env port перекрывает
    assert resolve_web(None, "9000", file_cfg) == ("127.0.0.1", 9000)
    # оба env перекрывают
    assert resolve_web("0.0.0.0", "9000", file_cfg) == ("0.0.0.0", 9000)
    # пустые строки = не заданы
    assert resolve_web("", "", file_cfg) == ("127.0.0.1", 8001)


def check_resolve_web_bad_host():
    # пустой host в файле и без env → ValueError
    try:
        resolve_web(None, None, {"web_host": "", "web_port": 8001})
    except ValueError as e:
        assert "host" in str(e).lower() or "WEB_HOST" in str(e), str(e)
    else:
        assert False, "ожидался ValueError на пустой web_host"



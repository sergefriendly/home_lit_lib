#!/usr/bin/python3
# -*- coding: utf-8 -*-
import importlib
import pkgutil
import sys


def iter_modules():
    package = importlib.import_module("checks")
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.endswith("_checks"):
            yield importlib.import_module(f"checks.{info.name}")


def main() -> int:
    total = 0
    for module in iter_modules():
        checks = [v for k, v in vars(module).items() if k.startswith("check_") and callable(v)]
        for check in checks:
            check()
            print(f"OK  {module.__name__}.{check.__name__}")
            total += 1
    print(f"\nВсе проверки прошли: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
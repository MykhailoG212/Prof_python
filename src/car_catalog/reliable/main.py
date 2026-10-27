"""Командний вхід до ЛР5."""

from pathlib import Path

from car_catalog.reliable.config import load_config
from car_catalog.reliable.exceptions import ApplicationError
from car_catalog.reliable.services import import_catalog


def main() -> int:
    try:
        report = import_catalog(load_config(Path("config/lab5.yaml")))
    except ApplicationError as error:
        print(f"Помилка: {error}")
        return 1
    print(f"Імпорт завершено: valid={report.valid_count}, invalid={report.invalid_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

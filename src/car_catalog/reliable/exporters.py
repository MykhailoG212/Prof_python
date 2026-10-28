"""JSON-експорт з атомарною заміною завершеного файла."""

import json
import os
from contextlib import contextmanager
from collections.abc import Callable, Iterable
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator, TextIO, cast

from car_catalog.reliable.exceptions import DataExportError


@contextmanager
def atomic_text_writer(path: Path) -> Generator[TextIO, None, None]:
    """Створює тимчасовий файл і замінює ціль лише після успішного запису."""
    temporary: Path | None = None
    active_error: Exception | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as file:
            temporary = Path(file.name)
            yield cast(TextIO, file)
        os.replace(temporary, path)
    except OSError as error:
        active_error = error
        raise DataExportError(f"Cannot export JSON to: {path}") from error
    except Exception as error:
        active_error = error
        raise
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as error:
                message = f"Cannot remove temporary export file {temporary}: {error}"
                if active_error is None:
                    raise DataExportError(message) from error
                active_error.add_note(message)


def export_json(
    path: Path,
    vehicles: Iterable[dict[str, int | float | str]],
    statistics: Callable[[], dict[str, int]],
) -> None:
    """Writes a JSON catalog incrementally without collecting records in RAM."""
    try:
        with atomic_text_writer(path) as target:
            target.write('{\n  "vehicles": [')
            first = True
            for vehicle in vehicles:
                target.write("\n    " if first else ",\n    ")
                json.dump(vehicle, target, ensure_ascii=False)
                first = False
            target.write('\n  ],\n  "statistics": ')
            json.dump(statistics(), target, ensure_ascii=False, indent=2)
            target.write("\n}\n")
    except (TypeError, ValueError) as error:
        raise DataExportError("JSON payload is not serializable") from error

"""JSON-експорт з атомарною заміною завершеного файла."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator, TextIO, cast

from car_catalog.reliable.exceptions import DataExportError


@contextmanager
def atomic_text_writer(path: Path) -> Iterator[TextIO]:
    """Створює тимчасовий файл і замінює ціль лише після успішного запису."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as file:
            temporary = Path(file.name)
            yield cast(TextIO, file)
        os.replace(temporary, path)
    except OSError as error:
        raise DataExportError(f"Cannot export JSON to: {path}") from error
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def export_json(path: Path, payload: dict[str, object]) -> None:
    try:
        with atomic_text_writer(path) as target:
            json.dump(payload, target, ensure_ascii=False, indent=2)
            target.write("\n")
    except (TypeError, ValueError) as error:
        raise DataExportError("JSON payload is not serializable") from error

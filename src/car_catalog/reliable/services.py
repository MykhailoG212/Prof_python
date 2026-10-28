"""Оркестрація strict/tolerant імпорту, статистики, логування та експорту."""

import logging
from dataclasses import dataclass
from pathlib import Path

from car_catalog.reliable.exceptions import ConfigurationError, DataImportError, RecordValidationError
from car_catalog.reliable.exporters import export_json
from car_catalog.reliable.importers import read_vehicles
from car_catalog.reliable.models import AppConfig


@dataclass(slots=True)
class ImportReport:
    valid_count: int = 0
    invalid_count: int = 0


def configure_logging(path: Path, level: str) -> logging.Logger:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("car_catalog.reliable")
        logger.handlers.clear()
        logger.setLevel(getattr(logging, level, logging.INFO))
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        return logger
    except OSError as error:
        raise ConfigurationError(f"Cannot initialize log file: {path}") from error


def import_catalog(config: AppConfig) -> ImportReport:
    """Імпортує каталог за політикою strict або tolerant та експортує valid записи."""
    logger = configure_logging(config.logging.path, config.logging.level)
    report = ImportReport()

    def valid_vehicles():
        for line_number, result in read_vehicles(config.input_path, config.processing):
            if isinstance(result, RecordValidationError):
                report.invalid_count += 1
                logger.warning("line=%s field=%s error=%s", line_number, result.field, result)
                if config.processing.invalid_record_policy == "strict":
                    raise DataImportError(f"Import stopped at line {line_number}: {result}") from result
                continue
            report.valid_count += 1
            yield result.to_dict()

    export_json(
        config.output_path,
        valid_vehicles(),
        lambda: {"valid": report.valid_count, "invalid": report.invalid_count},
    )
    logger.info("Import completed: valid=%s invalid=%s", report.valid_count, report.invalid_count)
    return report

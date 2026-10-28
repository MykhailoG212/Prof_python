"""Завантаження та fail-fast перевірка YAML-конфігурації."""

from pathlib import Path
from typing import Any, cast

from car_catalog.reliable.exceptions import ConfigurationError
from car_catalog.reliable.models import AppConfig, LoggingConfig, ProcessingConfig


def _scalar(value: str) -> str | int | float | bool:
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value.strip('"\'')


def _load_simple_yaml(path: Path) -> dict[str, dict[str, Any]]:
    """Читає обмежений, але достатній для конфігурації YAML без зовнішньої залежності."""
    result: dict[str, dict[str, Any]] = {}
    section: str | None = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}") from error
    except OSError as error:
        raise ConfigurationError(f"Cannot read configuration: {path}") from error

    for number, source in enumerate(lines, start=1):
        line = source.split("#", maxsplit=1)[0].rstrip()
        if not line:
            continue
        if not source.startswith((" ", "\t")):
            if not line.endswith(":"):
                raise ConfigurationError(f"Invalid YAML section at line {number}")
            section = line[:-1].strip()
            result[section] = {}
            continue
        if section is None or ":" not in line:
            raise ConfigurationError(f"Invalid YAML key at line {number}")
        key, raw_value = line.strip().split(":", maxsplit=1)
        result[section][key.strip()] = _scalar(raw_value)
    return result


def load_config(path: Path) -> AppConfig:
    """Повертає перевірену конфігурацію або завершує роботу до імпорту."""
    raw = _load_simple_yaml(path)
    try:
        processing = raw["processing"]
        policy = str(processing["invalid_record_policy"])
        if policy not in {"strict", "tolerant"}:
            raise ValueError("invalid_record_policy must be strict or tolerant")
        config = AppConfig(
            input_path=Path(str(raw["input"]["path"])),
            output_path=Path(str(raw["output"]["path"])),
            processing=ProcessingConfig(
                minimum_year=int(processing["minimum_year"]),
                maximum_year=int(processing["maximum_year"]),
                minimum_price=float(processing["minimum_price"]),
                maximum_price=float(processing["maximum_price"]),
                invalid_record_policy=cast("Any", policy),
            ),
            logging=LoggingConfig(
                level=str(raw["logging"]["level"]).upper(),
                path=Path(str(raw["logging"]["path"])),
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError("Invalid YAML configuration") from error
    if config.logging.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError("logging.level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    if config.processing.minimum_year > config.processing.maximum_year:
        raise ConfigurationError("minimum_year must not exceed maximum_year")
    if config.processing.minimum_price > config.processing.maximum_price:
        raise ConfigurationError("minimum_price must not exceed maximum_price")
    if not config.input_path.is_file():
        raise ConfigurationError(f"Input file does not exist: {config.input_path}")
    return config

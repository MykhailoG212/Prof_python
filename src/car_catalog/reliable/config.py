"""Завантаження та fail-fast перевірка YAML-конфігурації."""

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import yaml

from car_catalog.reliable.exceptions import ConfigurationError
from car_catalog.reliable.models import AppConfig, LoggingConfig, ProcessingConfig


def _load_yaml(path: Path) -> dict[str, dict[str, object]]:
    """Безпечно читає YAML і перевіряє структуру секцій."""
    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}") from error
    except OSError as error:
        raise ConfigurationError(f"Cannot read configuration: {path}") from error
    except UnicodeError as error:
        raise ConfigurationError(f"Configuration is not valid UTF-8: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML syntax in configuration: {path}") from error

    if not isinstance(raw, Mapping):
        raise ConfigurationError("YAML configuration must contain a mapping of sections")

    result: dict[str, dict[str, object]] = {}
    for section, values in raw.items():
        if not isinstance(section, str) or not isinstance(values, Mapping):
            raise ConfigurationError("YAML configuration sections must be named mappings")
        if not all(isinstance(key, str) for key in values):
            raise ConfigurationError(f"Keys in section {section!r} must be strings")
        result[section] = dict(values)
    return result


def _required(section: Mapping[str, object], key: str) -> object:
    try:
        return section[key]
    except KeyError as error:
        raise ConfigurationError(f"Missing configuration value: {key}") from error


def _integer(section: Mapping[str, object], key: str) -> int:
    value = _required(section, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer")
    return value


def _number(section: Mapping[str, object], key: str) -> float:
    value = _required(section, key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{key} must be a number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ConfigurationError(f"{key} is outside the supported numeric range") from error
    if not math.isfinite(number):
        raise ConfigurationError(f"{key} must be finite")
    return number


def _text(section: Mapping[str, object], key: str) -> str:
    value = _required(section, key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{key} must be a non-empty string")
    return value.strip()


def _resolve_path(section: Mapping[str, object], key: str, base: Path) -> Path:
    path = Path(_text(section, key))
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def load_config(path: Path) -> AppConfig:
    """Повертає перевірену конфігурацію або завершує роботу до імпорту."""
    raw = _load_yaml(path)
    try:
        input_config = raw["input"]
        output_config = raw["output"]
        processing = raw["processing"]
        logging_config = raw["logging"]
    except KeyError as error:
        raise ConfigurationError(f"Missing configuration section: {error.args[0]}") from error

    policy = _text(processing, "invalid_record_policy")
    if policy == "strict":
        invalid_record_policy: Literal["strict", "tolerant"] = "strict"
    elif policy == "tolerant":
        invalid_record_policy = "tolerant"
    else:
        raise ConfigurationError("invalid_record_policy must be strict or tolerant")

    minimum_price = _number(processing, "minimum_price")
    maximum_price = _number(processing, "maximum_price")
    if minimum_price < 0:
        raise ConfigurationError("minimum_price must not be negative")
    if minimum_price > maximum_price:
        raise ConfigurationError("minimum_price must not exceed maximum_price")

    config = AppConfig(
        input_path=_resolve_path(input_config, "path", path.resolve().parent),
        output_path=_resolve_path(output_config, "path", path.resolve().parent),
        processing=ProcessingConfig(
            minimum_year=_integer(processing, "minimum_year"),
            maximum_year=_integer(processing, "maximum_year"),
            minimum_price=minimum_price,
            maximum_price=maximum_price,
            invalid_record_policy=invalid_record_policy,
        ),
        logging=LoggingConfig(
            level=_text(logging_config, "level").upper(),
            path=_resolve_path(logging_config, "path", path.resolve().parent),
        ),
    )
    if config.logging.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError("logging.level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    if config.processing.minimum_year > config.processing.maximum_year:
        raise ConfigurationError("minimum_year must not exceed maximum_year")
    if len({config.input_path, config.output_path, config.logging.path}) != 3:
        raise ConfigurationError("input, output, and logging paths must be different")
    if not config.input_path.is_file():
        raise ConfigurationError(f"Input file does not exist: {config.input_path}")
    return config

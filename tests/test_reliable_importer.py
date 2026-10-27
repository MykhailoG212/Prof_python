"""Перевірки надійного CSV → JSON конвеєра ЛР5."""

import json
from pathlib import Path

import pytest

from car_catalog.reliable.config import load_config
from car_catalog.reliable.exceptions import ConfigurationError, DataImportError
from car_catalog.reliable.exporters import atomic_text_writer
from car_catalog.reliable.services import import_catalog


def write_config(path: Path, *, policy: str = "tolerant") -> Path:
    input_path = path.parent / "vehicles.csv"
    output_path = path.parent / "output" / "vehicles.json"
    log_path = path.parent / "logs" / "lab5.log"
    path.write_text(
        "\n".join(
            [
                "input:", f"  path: {input_path.as_posix()}",
                "output:", f"  path: {output_path.as_posix()}",
                "processing:", "  minimum_year: 1886", "  maximum_year: 2026",
                "  minimum_price: 0", "  maximum_price: 1000000",
                f"  invalid_record_policy: {policy}",
                "logging:", "  level: INFO", f"  path: {log_path.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    return input_path


def write_csv(path: Path) -> None:
    path.write_text(
        "vehicle_id,brand,model,year,price,mileage\n"
        "1,Tesla,Model Y,2023,50000,12000\n"
        "bad,Toyota,Camry,2020,25000,30000\n"
        "2,BMW,M3,2022,72000,24000\n",
        encoding="utf-8",
    )


def test_tolerant_import_exports_only_valid_records_and_logs_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    input_path = write_config(config_path)
    write_csv(input_path)

    config = load_config(config_path)
    report = import_catalog(config)

    assert (report.valid_count, report.invalid_count) == (2, 1)
    payload = json.loads(config.output_path.read_text(encoding="utf-8"))
    assert payload["statistics"] == {"valid": 2, "invalid": 1}
    assert [vehicle["vehicle_id"] for vehicle in payload["vehicles"]] == [1, 2]
    assert "numeric field has invalid value" in config.logging.path.read_text(encoding="utf-8")


def test_strict_import_stops_and_does_not_create_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    input_path = write_config(config_path, policy="strict")
    write_csv(input_path)
    config = load_config(config_path)

    with pytest.raises(DataImportError, match="line 3") as error:
        import_catalog(config)

    assert error.value.__cause__ is not None
    assert not config.output_path.exists()


def test_invalid_config_fails_before_processing(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.yaml"
    config_path.write_text("processing:\n  minimum_year: 2025\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_config(config_path)


def test_atomic_writer_preserves_existing_file_after_failure(tmp_path: Path) -> None:
    target = tmp_path / "output.json"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with atomic_text_writer(target) as target_file:
            target_file.write("new")
            raise RuntimeError("export failure")

    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob("*.tmp")) == []

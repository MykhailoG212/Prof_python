"""Перевірки надійного CSV → JSON конвеєра ЛР5."""

import json
from pathlib import Path

import pytest

from car_catalog.reliable.config import load_config
from car_catalog.reliable.benchmark import compare_processing, write_synthetic_dataset
from car_catalog.reliable.exceptions import ConfigurationError, DataImportError, RecordValidationError
from car_catalog.reliable.exporters import atomic_text_writer
from car_catalog.reliable.importers import parse_vehicle
from car_catalog.reliable.models import ProcessingConfig
from car_catalog.reliable.services import import_catalog

pytestmark = pytest.mark.integration


def write_config(path: Path, *, policy: str = "tolerant") -> Path:
    input_path = path.parent / "vehicles.csv"
    path.write_text(
        "\n".join(
            [
                "input:", "  path: vehicles.csv",
                "output:", "  path: output/vehicles.json",
                "processing:", "  minimum_year: 1886", "  maximum_year: 2026",
                "  minimum_price: 0", "  maximum_price: 1000000",
                f"  invalid_record_policy: {policy}",
                "logging:", "  level: INFO", "  path: logs/lab5.log",
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
    config.output_path.parent.mkdir(parents=True)
    config.output_path.write_text("previous valid export", encoding="utf-8")

    with pytest.raises(DataImportError, match="line 3") as error:
        import_catalog(config)

    assert error.value.__cause__ is not None
    assert config.output_path.read_text(encoding="utf-8") == "previous valid export"
    assert list(config.output_path.parent.glob("*.tmp")) == []


def test_invalid_config_fails_before_processing(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.yaml"
    config_path.write_text("input: [", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid YAML syntax"):
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


def test_tolerant_import_counts_rows_with_extra_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    input_path = write_config(config_path)
    input_path.write_text(
        "vehicle_id,brand,model,year,price,mileage\n"
        "1,Tesla,Model Y,2023,50000,12000,unexpected\n"
        "2,BMW,M3,2022,72000,24000\n",
        encoding="utf-8",
    )

    config = load_config(config_path)
    report = import_catalog(config)

    assert (report.valid_count, report.invalid_count) == (1, 1)
    payload = json.loads(config.output_path.read_text(encoding="utf-8"))
    assert [vehicle["vehicle_id"] for vehicle in payload["vehicles"]] == [2]
    assert "different number of fields" in config.logging.path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "header",
    [
        "vehicle_id,brand,brand,year,price,mileage",
        "vehicle_id,brand,model,year,price,mileage,unexpected",
    ],
)
def test_invalid_csv_header_fails_before_export(tmp_path: Path, header: str) -> None:
    config_path = tmp_path / "config.yaml"
    input_path = write_config(config_path)
    input_path.write_text(header + "\n", encoding="utf-8")
    config = load_config(config_path)

    with pytest.raises(DataImportError, match="CSV header"):
        import_catalog(config)

    assert not config.output_path.exists()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"vehicle_id,brand,model,year,price,mileage\n1,Tesla,\"unfinished", "Malformed CSV"),
        (b"vehicle_id,brand,model,year,price,mileage\n\xff", "UTF-8"),
    ],
)
def test_unreadable_csv_fails_without_committing_output(
    tmp_path: Path, payload: bytes, message: str
) -> None:
    config_path = tmp_path / "config.yaml"
    input_path = write_config(config_path)
    input_path.write_bytes(payload)
    config = load_config(config_path)

    with pytest.raises(DataImportError, match=message):
        import_catalog(config)

    assert not config.output_path.exists()


def test_config_resolves_paths_relative_to_config_file(tmp_path: Path) -> None:
    config_path = tmp_path / "nested" / "config.yaml"
    config_path.parent.mkdir()
    input_path = config_path.parent / "vehicles.csv"
    input_path.write_text("vehicle_id,brand,model,year,price,mileage\n", encoding="utf-8")
    config_path.write_text(
        "input:\n  path: vehicles.csv\n"
        "output:\n  path: output/vehicles.json\n"
        "processing:\n  minimum_year: 1886\n  maximum_year: 2026\n"
        "  minimum_price: 0\n  maximum_price: 1000000\n"
        "  invalid_record_policy: tolerant\n"
        "logging:\n  level: INFO\n  path: logs/lab5.log\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.input_path == input_path.resolve()
    assert config.output_path == (config_path.parent / "output/vehicles.json").resolve()


@pytest.mark.parametrize(
    ("minimum_price", "maximum_price"),
    [("-1", "100"), (".nan", "100"), ("0", ".inf")],
)
def test_invalid_price_range_is_rejected(
    tmp_path: Path, minimum_price: str, maximum_price: str
) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    content = config_path.read_text(encoding="utf-8")
    content = content.replace("minimum_price: 0", f"minimum_price: {minimum_price}")
    content = content.replace("maximum_price: 1000000", f"maximum_price: {maximum_price}")
    config_path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(config_path)


def test_csv_header_with_utf8_bom_is_supported(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    input_path = write_config(config_path)
    input_path.write_text(
        "\ufeffvehicle_id,brand,model,year,price,mileage\n"
        "1,Tesla,Model Y,2023,50000,12000\n",
        encoding="utf-8",
    )
    config = load_config(config_path)

    report = import_catalog(config)

    assert (report.valid_count, report.invalid_count) == (1, 0)


def test_eager_and_streaming_benchmark_results_match(tmp_path: Path) -> None:
    input_path = tmp_path / "vehicles.csv"
    write_synthetic_dataset(input_path, size=20, invalid_every=10)

    eager, streaming = compare_processing(input_path)

    assert eager.summary == streaming.summary
    assert eager.summary.valid_count == 20
    assert eager.summary.invalid_count == 2
    assert eager.peak_memory_bytes > streaming.peak_memory_bytes


def test_vehicle_parser_rejects_negative_price_even_if_config_allows_it() -> None:
    config = ProcessingConfig(
        minimum_year=1886,
        maximum_year=2026,
        minimum_price=-100,
        maximum_price=100_000,
        invalid_record_policy="tolerant",
    )
    row = {
        "vehicle_id": "1",
        "brand": "Tesla",
        "model": "Model Y",
        "year": "2023",
        "price": "-1",
        "mileage": "12000",
    }

    with pytest.raises(RecordValidationError, match="price must be non-negative"):
        parse_vehicle(row, line_number=2, config=config)

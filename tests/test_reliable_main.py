from pathlib import Path

import pytest

from car_catalog.reliable.models import AppConfig, LoggingConfig, ProcessingConfig
from car_catalog.reliable.exceptions import ConfigurationError
from car_catalog.reliable.services import ImportReport
import car_catalog.reliable.main as reliable_main


@pytest.mark.parametrize(
    ("configured_path", "environment_value"),
    [
        ("custom/config.yaml", "custom/config.yaml"),
        ("config/lab5.yaml", None),
    ],
    ids=["environment-override", "default-path"],
)
def test_cli_uses_environment_config_or_default(
    monkeypatch: pytest.MonkeyPatch,
    configured_path: str,
    environment_value: str | None,
) -> None:
    if environment_value is None:
        monkeypatch.delenv("CAR_CATALOG_CONFIG", raising=False)
    else:
        monkeypatch.setenv("CAR_CATALOG_CONFIG", environment_value)

    loaded_paths: list[Path] = []

    def fake_load_config(path: Path) -> AppConfig:
        loaded_paths.append(path)
        return AppConfig(
            input_path=Path("vehicles.csv"),
            output_path=Path("vehicles.json"),
            processing=ProcessingConfig(
                minimum_year=1886,
                maximum_year=2026,
                minimum_price=0.0,
                maximum_price=1_000_000.0,
                invalid_record_policy="tolerant",
            ),
            logging=LoggingConfig(level="INFO", path=Path("lab5.log")),
        )

    monkeypatch.setattr(reliable_main, "load_config", fake_load_config)
    monkeypatch.setattr(
        reliable_main,
        "import_catalog",
        lambda _config: ImportReport(valid_count=2, invalid_count=1),
    )

    assert reliable_main.main() == 0
    assert loaded_paths == [Path(configured_path)]


def test_cli_reports_configuration_failure_without_importing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_to_load(_path: Path) -> AppConfig:
        raise ConfigurationError("invalid test configuration")

    def unexpected_import(_config: AppConfig) -> ImportReport:
        pytest.fail("import must not start when configuration is invalid")

    monkeypatch.setattr(reliable_main, "load_config", fail_to_load)
    monkeypatch.setattr(reliable_main, "import_catalog", unexpected_import)

    assert reliable_main.main() == 1
    assert "Помилка: invalid test configuration" in capsys.readouterr().out

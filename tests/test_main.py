import pytest

from car_catalog.main import create_car_from_input, get_demo_cars, run_menu
from car_catalog.models import Car


def test_create_car_from_input_retries_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(
        [
            " ",
            "Toyota",
            "Camry",
            "not-a-year",
            "1800",
            "2021",
            "not-a-price",
            "-1",
            "nan",
            "22000",
            "-1",
            "30000",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    car = create_car_from_input()

    assert car == Car("Toyota", "Camry", 2021, 22000.0, 30000)


def test_menu_adds_car_to_catalog(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter(["7", "Toyota", "Corolla", "2019", "18000", "10000", "8"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    catalog = get_demo_cars()

    run_menu(catalog)

    assert len(catalog) == 5
    assert catalog[-1] == Car("Toyota", "Corolla", 2019, 18000.0, 10000)
    assert "Автомобіль додано до каталогу." in capsys.readouterr().out

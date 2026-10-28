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


def test_menu_runs_lab3_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["11", "8"])
    called = False

    def run_demo() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("car_catalog.main.run_lab3_demo", run_demo)

    run_menu([])

    assert called


def test_menu_handles_invalid_year_empty_results_and_all_demos(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(
        [
            "1",
            "2", "Tesla",
            "3", "not-a-year",
            "3", "2020",
            "4", "5", "6",
            "9", "10", "11", "12", "13",
            "unknown",
            "8",
        ]
    )
    calls: list[str] = []
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("car_catalog.main.print_cars", lambda _cars: None)
    monkeypatch.setattr("car_catalog.main.find_by_brand", lambda _cars, _brand: [])
    monkeypatch.setattr("car_catalog.main.filter_by_year", lambda _cars, _year: [])
    monkeypatch.setattr("car_catalog.main.run_lab2_demo", lambda *_args: calls.append("lab2"))
    monkeypatch.setattr("car_catalog.main.run_benchmark", lambda: calls.append("benchmark"))
    monkeypatch.setattr("car_catalog.main.run_lab3_demo", lambda: calls.append("lab3"))
    monkeypatch.setattr(
        "car_catalog.main.run_streaming_benchmark",
        lambda: calls.append("streaming benchmark"),
    )
    monkeypatch.setattr("car_catalog.main.run_lab4_demo", lambda: calls.append("lab4"))

    run_menu([])

    output = capsys.readouterr().out
    assert "Помилка: введіть коректне число для року." in output
    assert "Невідома команда." in output
    assert "Каталог порожній." in output
    assert "Роботу завершено." in output
    assert calls == ["lab2", "benchmark", "lab3", "streaming benchmark", "lab4"]

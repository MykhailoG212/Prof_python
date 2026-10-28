import math
from collections import deque

import uvicorn

from car_catalog.analytics import (
    calculate_total_and_average_price,
    calculate_variadic_average,
    create_car_record,
    create_min_year_filter,
    create_price_range_filter,
    filter_cars,
    find_most_expensive_car,
    sort_cars_by_price,
)
from car_catalog.benchmark import run_benchmark
from car_catalog.models import Car
from car_catalog.oop_demo import run_demo as run_lab4_demo
from car_catalog.processors import (
    build_cars_by_id_index,
    count_cars_by_brand,
    extract_cars_brief_tuples,
    get_unique_brands,
    group_cars_by_brand,
)
from car_catalog.services import (
    calculate_average_price,
    filter_by_year,
    find_by_brand,
    find_lowest_mileage,
    find_most_expensive,
)
from car_catalog.streaming.benchmark import run_benchmark as run_streaming_benchmark
from car_catalog.streaming.demo import run_demo as run_lab3_demo
from car_catalog.config import get_settings
from car_catalog.logging_config import configure_logging


def get_demo_cars() -> list[Car]:
    return [
        Car(brand="Tesla", model="Model Y Performance", year=2023, price=50000.0, mileage=12000),
        Car(brand="Toyota", model="Camry", year=2020, price=25000.0, mileage=45000),
        Car(brand="Honda", model="Civic", year=2021, price=22000.0, mileage=30000),
        Car(brand="Toyota", model="Corolla", year=2019, price=18000.0, mileage=60000),
    ]


def print_cars(cars: list[Car]) -> None:
    if not cars:
        print("\n[Список порожній]")
        return

    print("\n" + "=" * 70)
    print(f"{'Марка та Модель':<30} | {'Рік':<6} | {'Ціна, $':<12} | {'Пробіг, км':<10}")
    print("-" * 70)
    for car in cars:
        print(
            f"{car.full_name:25} | Рік: {car.year:4} | Ціна: ${car.price:8.2f} | Пробіг: {car.mileage:7} км"
        )
    print("=" * 70)


def print_menu() -> None:
    print("\n--- КАТАЛОГ АВТОМОБІЛІВ ---")
    print("1. Показати всі автомобілі")
    print("2. Пошук за маркою")
    print("3. Фільтрація за роком випуску")
    print("4. Знайти найдорожчий автомобіль")
    print("5. Знайти авто з найменшим пробігом")
    print("6. Розрахувати середню ціну")
    print("7. Додати автомобіль")
    print("8. Вийти")
    print("9. Демонстрація можливостей ЛР2")
    print("10. Benchmark пошуку list vs dict")
    print("11. Демонстрація потокової обробки ЛР3")
    print("12. Benchmark eager vs lazy для 100 000 записів")
    print("13. Демонстрація типізованої ООП-моделі ЛР4")


def _read_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Поле не може бути порожнім.")


def _read_int(prompt: str, minimum: int, error_message: str) -> int:
    while True:
        try:
            value = int(input(prompt).strip())
        except ValueError:
            print("Помилка: введіть ціле число.")
            continue
        if value < minimum:
            print(error_message)
            continue
        return value


def _read_price() -> float:
    while True:
        try:
            price = float(input("Введіть ціну в USD: ").strip())
        except ValueError:
            print("Помилка: введіть коректне число для ціни.")
            continue
        if not math.isfinite(price) or price < 0:
            print("Ціна має бути невід'ємним скінченним числом.")
            continue
        return price


def create_car_from_input() -> Car:
    brand = _read_non_empty("Введіть марку автомобіля: ")
    model = _read_non_empty("Введіть модель автомобіля: ")
    year = _read_int("Введіть рік випуску: ", 1886, "Рік випуску має бути не раніше 1886.")
    price = _read_price()
    mileage = _read_int("Введіть пробіг у кілометрах: ", 0, "Пробіг не може бути від'ємним.")
    return Car(brand=brand, model=model, year=year, price=price, mileage=mileage)


def run_lab2_demo(catalog: list[Car], history: deque[str]) -> None:
    unique_brands = get_unique_brands(catalog)
    print(f"\n[set comprehension] Унікальні марки: {unique_brands}")

    counts = count_cars_by_brand(catalog)
    print(f"[Counter] Кількість авто за марками: {dict(counts)}")

    grouped = group_cars_by_brand(catalog)
    print(f"[defaultdict] Кількість груп за марками: {len(grouped)}")

    car_index = build_cars_by_id_index(catalog)
    print(f"[dict comprehension] Автомобіль з ID 1: {car_index.get(1)}")

    brief_records = extract_cars_brief_tuples(catalog)
    print(f"[list comprehension + tuple] Перші записи: {brief_records[:3]}")

    price_filter = create_price_range_filter(20_000.0, 75_000.0)
    filtered_cars = filter_cars(catalog, price_filter)
    print(
        "[closure + higher-order filter] Авто за ціною $20,000-$75,000: "
        f"{[car.full_name for car in filtered_cars]}"
    )

    recent_cars = filter_cars(catalog, create_min_year_filter(2021))
    print(f"[closure filter] Авто від 2021 року: {[car.full_name for car in recent_cars]}")

    sorted_cars = sort_cars_by_price(catalog, descending=True)
    print(f"[lambda sort] Найдорожчі авто: {[car.full_name for car in sorted_cars[:3]]}")
    print(
        f"[*args] Середня ціна: ${calculate_variadic_average(*(car.price for car in catalog)):,.2f}"
    )

    created_car = create_car_record(
        brand="Mercedes-Benz",
        model="AMG GT",
        year=2022,
        price=115_000.0,
        mileage=8_000,
    )
    print(f"[**kwargs] Створено запис: {created_car.full_name}")

    total, average = calculate_total_and_average_price(catalog)
    print(f"[generator aggregation] Загальна ціна: ${total:,.2f}; середня: ${average:,.2f}")
    most_expensive = find_most_expensive_car(catalog)
    if most_expensive is not None:
        print(f"[lambda aggregation] Найдорожчий автомобіль: {most_expensive.full_name}")

    history.append("Виконано демонстрацію ЛР2")
    print(f"[deque] Останні операції: {list(history)}")


def run_menu(catalog: list[Car]) -> None:
    history: deque[str] = deque(maxlen=3)
    while True:
        print_menu()
        choice = input("Оберіть дію: ").strip()

        if choice == "1":
            print_cars(catalog)
            history.append("Переглянуто каталог")

        elif choice == "2":
            make = input("Введіть марку для пошуку: ").strip()
            results = find_by_brand(catalog, make)
            print_cars(results)
            history.append(f"Пошук марки: {make}")

        elif choice == "3":
            raw_year = input("Введіть рік: ").strip()
            try:
                year = int(raw_year)
                results = filter_by_year(catalog, year)
                print_cars(results)
                history.append(f"Фільтр за роком: {year}")
            except ValueError:
                print("Помилка: введіть коректне число для року.")

        elif choice == "4":
            car = find_most_expensive(catalog)
            if car:
                print(f"\nНайдорожче авто: {car.full_name} — ${car.price:,.2f}")
            else:
                print("\nКаталог порожній.")
            history.append("Знайдено найдорожче авто")

        elif choice == "5":
            car = find_lowest_mileage(catalog)
            if car:
                print(f"\nАвто з найменшим пробігом: {car.full_name} — {car.mileage:,} км")
            else:
                print("\nКаталог порожній.")
            history.append("Знайдено авто з найменшим пробігом")

        elif choice == "6":
            avg = calculate_average_price(catalog)
            print(f"\nСередня ціна авто в каталозі: ${avg:,.2f}")
            history.append("Обчислено середню ціну")

        elif choice == "7":
            catalog.append(create_car_from_input())
            print("Автомобіль додано до каталогу.")
            history.append("Додано автомобіль")

        elif choice == "8":
            print("\nРоботу завершено.")
            break
        elif choice == "9":
            run_lab2_demo(catalog, history)
        elif choice == "10":
            run_benchmark()
            history.append("Виконано benchmark list vs dict")
        elif choice == "11":
            run_lab3_demo()
            history.append("Виконано потокову демонстрацію ЛР3")
        elif choice == "12":
            run_streaming_benchmark()
            history.append("Виконано benchmark eager vs lazy")
        elif choice == "13":
            run_lab4_demo()
            history.append("Виконано демонстрацію ООП-моделі ЛР4")
        else:
            print("\nНевідома команда. Спробуйте ще раз.")


def run_demo() -> None:
    catalog = get_demo_cars()
    run_menu(catalog)


def main() -> None:
    """Start the production HTTP API."""
    settings = get_settings()
    configure_logging(settings)
    uvicorn.run(
        "car_catalog.api:app",
        host=settings.host,
        port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()

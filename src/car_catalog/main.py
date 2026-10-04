import math

from car_catalog.models import Car
from car_catalog.services import (
    calculate_average_price,
    filter_by_year,
    find_by_brand,
    find_lowest_mileage,
    find_most_expensive,
)


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
        print(f"{car.full_name:25} | Рік: {car.year:4} | Ціна: ${car.price:8.2f} | Пробіг: {car.mileage:7} км")
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


def run_menu(catalog: list[Car]) -> None:
    while True:
        print_menu()
        choice = input("Оберіть дію: ").strip()

        if choice == "1":
            print_cars(catalog)

        elif choice == "2":
            make = input("Введіть марку для пошуку: ").strip()
            results = find_by_brand(catalog, make)
            print_cars(results)

        elif choice == "3":
            raw_year = input("Введіть рік: ").strip()
            try:
                year = int(raw_year)
                results = filter_by_year(catalog, year)
                print_cars(results)
            except ValueError:
                print("Помилка: введіть коректне число для року.")

        elif choice == "4":
            car = find_most_expensive(catalog)
            if car:
                print(f"\nНайдорожче авто: {car.full_name} — ${car.price:,.2f}")
            else:
                print("\nКаталог порожній.")

        elif choice == "5":
            car = find_lowest_mileage(catalog)
            if car:
                print(f"\nАвто з найменшим пробігом: {car.full_name} — {car.mileage:,} км")
            else:
                print("\nКаталог порожній.")

        elif choice == "6":
            avg = calculate_average_price(catalog)
            print(f"\nСередня ціна авто в каталозі: ${avg:,.2f}")

        elif choice == "7":
            catalog.append(create_car_from_input())
            print("Автомобіль додано до каталогу.")

        elif choice == "8":
            print("\nРоботу завершено.")
            break
        else:
            print("\nНевідома команда. Спробуйте ще раз.")


def main() -> None:
    catalog = get_demo_cars()
    run_menu(catalog)


if __name__ == "__main__":
    main()

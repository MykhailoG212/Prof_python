"""Interactive CLI backed by the SQLite persistence layer."""

import math

from sqlalchemy.exc import IntegrityError

from car_catalog.persistence.database import Database
from car_catalog.persistence.models import CarRecord
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository
from car_catalog.persistence.services import CarCatalogService


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


def _read_price(prompt: str = "Введіть ціну в USD: ") -> float:
    while True:
        try:
            price = float(input(prompt).strip())
        except ValueError:
            print("Помилка: введіть коректне число для ціни.")
            continue
        if not math.isfinite(price) or price < 0:
            print("Ціна має бути невід'ємним скінченним числом.")
            continue
        return price


def _print_cars(cars: list[CarRecord]) -> None:
    if not cars:
        print("\nКаталог порожній.")
        return
    print("\nID | Марка та модель | Рік | Ціна, USD | Пробіг, км | VIN")
    for car in cars:
        print(
            f"{car.id} | {car.manufacturer.name} {car.model} | {car.year} | "
            f"${car.price:,.2f} | {car.mileage:,} | {car.vin}"
        )


def _add_car(database: Database) -> None:
    manufacturer_name = _read_non_empty("Введіть марку автомобіля: ")
    model = _read_non_empty("Введіть модель автомобіля: ")
    year = _read_int("Введіть рік випуску: ", 1886, "Рік випуску має бути не раніше 1886.")
    price = _read_price()
    mileage = _read_int("Введіть пробіг у кілометрах: ", 0, "Пробіг не може бути від'ємним.")
    vin = _read_non_empty("Введіть VIN: ")

    with database.session_factory.begin() as session:
        manufacturers = ManufacturerRepository(session)
        manufacturer = manufacturers.get_by_name(manufacturer_name)
        if manufacturer is None:
            manufacturer = manufacturers.create(manufacturer_name)
        car = CarRepository(session).create(
            manufacturer_id=manufacturer.id,
            model=model,
            year=year,
            price=price,
            mileage=mileage,
            vin=vin,
        )
    print(f"Автомобіль додано до каталогу (ID {car.id}).")


def _update_car(database: Database) -> None:
    car_id = _read_int("Введіть ID автомобіля: ", 1, "ID має бути додатним.")
    price = _read_price("Введіть нову ціну в USD: ")
    mileage = _read_int("Введіть новий пробіг у кілометрах: ", 0, "Пробіг не може бути від'ємним.")
    with database.session_factory.begin() as session:
        car = CarRepository(session).update(car_id, price=price, mileage=mileage)
        if car is None:
            print(f"Автомобіль з ID {car_id} не знайдено.")
            return
    print("Ціну та пробіг оновлено.")


def _delete_car(database: Database) -> None:
    car_id = _read_int("Введіть ID автомобіля: ", 1, "ID має бути додатним.")
    with database.session_factory.begin() as session:
        deleted = CarRepository(session).delete(car_id)
    if deleted:
        print("Автомобіль видалено.")
    else:
        print(f"Автомобіль з ID {car_id} не знайдено.")


def _update_manufacturer_prices(database: Database) -> None:
    manufacturer_name = _read_non_empty("Введіть марку автомобіля: ")
    try:
        percentage = float(input("Введіть відсоток зміни ціни (наприклад, 5 або -10): ").strip())
    except ValueError:
        print("Помилка: введіть коректний відсоток.")
        return
    if not math.isfinite(percentage) or percentage <= -100:
        print("Відсоток має бути скінченним і більшим за -100.")
        return

    with database.session_factory() as session:
        cars = CarRepository(session).find_by_manufacturer(manufacturer_name)
        if not cars:
            print(f"Автомобілі марки «{manufacturer_name}» не знайдено.")
            return
        manufacturer_id = cars[0].manufacturer_id
        multiplier = 1 + percentage / 100
        price_updates: dict[int, float] = {}
        for car in cars:
            updated_price = car.price * multiplier
            if not math.isfinite(updated_price):
                raise ValueError(f"Updated price for car {car.id} is not finite")
            price_updates[car.id] = round(updated_price, 2)

    updated_count = CarCatalogService(database.session_factory).update_prices_for_manufacturer(
        manufacturer_id,
        price_updates,
    )
    print(f"Ціни оновлено для автомобілів: {updated_count}.")


def run_menu(database: Database) -> None:
    """Run the persistent catalog menu until the user chooses to exit."""
    database.create_schema()
    while True:
        print(
            "\n--- КАТАЛОГ АВТОМОБІЛІВ (SQLite) ---\n"
            "1. Показати всі автомобілі\n"
            "2. Пошук за маркою\n"
            "3. Фільтрація за роком\n"
            "4. Найдорожчий автомобіль\n"
            "5. Автомобіль з найменшим пробігом\n"
            "6. Середня ціна\n"
            "7. Додати автомобіль\n"
            "8. Змінити ціну та пробіг\n"
            "9. Видалити автомобіль\n"
            "10. Масово змінити ціни марки\n"
            "0. Вийти"
        )
        choice = input("Оберіть дію: ").strip()
        try:
            if choice == "0":
                print("Роботу завершено.")
                return
            if choice == "1":
                with database.session_factory() as session:
                    _print_cars(CarRepository(session).list_all())
            elif choice == "2":
                name = _read_non_empty("Введіть марку для пошуку: ")
                with database.session_factory() as session:
                    _print_cars(CarRepository(session).find_by_manufacturer(name))
            elif choice == "3":
                year = _read_int("Введіть рік: ", 1886, "Рік має бути не раніше 1886.")
                with database.session_factory() as session:
                    _print_cars(CarRepository(session).filter_by_year(year))
            elif choice == "4":
                with database.session_factory() as session:
                    car = CarRepository(session).most_expensive()
                    _print_cars([car] if car is not None else [])
            elif choice == "5":
                with database.session_factory() as session:
                    car = CarRepository(session).lowest_mileage()
                    _print_cars([car] if car is not None else [])
            elif choice == "6":
                with database.session_factory() as session:
                    print(f"Середня ціна: ${CarRepository(session).average_price():,.2f}")
            elif choice == "7":
                _add_car(database)
            elif choice == "8":
                _update_car(database)
            elif choice == "9":
                _delete_car(database)
            elif choice == "10":
                _update_manufacturer_prices(database)
            else:
                print("Невідома команда. Спробуйте ще раз.")
        except (IntegrityError, LookupError, ValueError) as error:
            print(f"Операцію не виконано: {error}")


def main() -> int:
    """Start the persistent CLI and close its database connections on exit."""
    database = Database()
    try:
        run_menu(database)
    finally:
        database.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from car_catalog.models import Car
from car_catalog.services import (
    calculate_average_price,
    filter_by_make,
    filter_by_year,
    find_lowest_mileage_car,
    find_most_expensive_car,
)


def get_demo_cars() -> list[Car]:
    return [
        Car(make="Tesla", model="Model Y Performance", year=2023, price=54000.0, mileage=18500),
        Car(make="BMW", model="M3 Competition", year=2022, price=72000.0, mileage=24000),
        Car(make="Audi", model="RS6 Avant", year=2021, price=108000.0, mileage=45000),
        Car(make="Tesla", model="Model 3 Long Range", year=2022, price=38000.0, mileage=32000),
        Car(make="Porsche", model="911 Carrera S", year=2023, price=132000.0, mileage=9200),
    ]


def print_cars_table(cars: list[Car]) -> None:
    if not cars:
        print("\n[Список порожній]")
        return

    print("\n" + "=" * 70)
    print(f"{'Марка та Модель':<30} | {'Рік':<6} | {'Ціна, $':<12} | {'Пробіг, км':<10}")
    print("-" * 70)
    for car in cars:
        print(f"{car.display_name:<30} | {car.year:<6} | {car.price:<12,.2f} | {car.mileage:<10,}")
    print("=" * 70)


def print_menu() -> None:
    print("\n--- КАТАЛОГ АВТОМОБІЛІВ ---")
    print("1. Показати всі автомобілі")
    print("2. Пошук за маркою")
    print("3. Фільтрація за роком випуску")
    print("4. Знайти найдорожчий автомобіль")
    print("5. Знайти авто з найменшим пробігом")
    print("6. Розрахувати середню ціну")
    print("0. Вихід")


def run_menu(catalog: list[Car]) -> None:
    while True:
        print_menu()
        choice = input("Оберіть дію: ").strip()

        if choice == "1":
            print_cars_table(catalog)

        elif choice == "2":
            make = input("Введіть марку для пошуку: ").strip()
            results = filter_by_make(catalog, make)
            print_cars_table(results)

        elif choice == "3":
            raw_year = input("Введіть рік: ").strip()
            try:
                year = int(raw_year)
                results = filter_by_year(catalog, year)
                print_cars_table(results)
            except ValueError:
                print("Помилка: введіть коректне число для року.")

        elif choice == "4":
            car = find_most_expensive_car(catalog)
            if car:
                print(f"\nНайдорожче авто: {car.display_name} — ${car.price:,.2f}")
            else:
                print("\nКаталог порожній.")

        elif choice == "5":
            car = find_lowest_mileage_car(catalog)
            if car:
                print(f"\nАвто з найменшим пробігом: {car.display_name} — {car.mileage:,} км")
            else:
                print("\nКаталог порожній.")

        elif choice == "6":
            avg = calculate_average_price(catalog)
            print(f"\nСередня ціна авто в каталозі: ${avg:,.2f}")

        elif choice == "0":
            print("\nРоботу завершено.")
            break
        else:
            print("\nНевідома команда. Спробуйте ще раз.")


def main() -> None:
    catalog = get_demo_cars()
    run_menu(catalog)


if __name__ == "__main__":
    main()

"""Порівняння лінійного пошуку в list з пошуком за ключем у dict."""

from time import perf_counter

from car_catalog.models import Car


def generate_dataset(size: int) -> list[Car]:
    """Генерує набір автомобілів із детермінованими, унікальними моделями."""
    if size < 1:
        raise ValueError("Розмір набору має бути додатним.")
    return [
        Car(
            brand=f"Brand_{index % 50}",
            model=f"Model_{index}",
            year=2000 + index % 25,
            price=10_000.0 + index % 50_000,
            mileage=index * 10,
        )
        for index in range(size)
    ]


def benchmark_lookup(size: int) -> tuple[float, float]:
    """Повертає час пошуку останнього запису через list та dict."""
    cars = generate_dataset(size)
    target_id = size
    target = cars[-1]
    records = list(enumerate(cars, start=1))
    index = {car_id: car for car_id, car in records}
    iterations = 100

    found_in_list = next(
        (car for car_id, car in records if car_id == target_id),
        None,
    )
    found_in_dict = index.get(target_id)
    if found_in_list is not target or found_in_dict is not target:
        raise RuntimeError("Пошук у list та dict повернув різні результати.")

    start = perf_counter()
    for _ in range(iterations):
        next(car for car_id, car in records if car_id == target_id)
    list_elapsed = (perf_counter() - start) / iterations

    start = perf_counter()
    for _ in range(iterations):
        index.get(target_id)
    dict_elapsed = (perf_counter() - start) / iterations
    return list_elapsed, dict_elapsed


def run_benchmark() -> None:
    """Виводить результати benchmark для 1 000, 10 000 і 100 000 записів."""
    sizes = (1_000, 10_000, 100_000)
    print("\nПорівняння пошуку останнього автомобіля (побудова індексу не вимірюється)")
    print(f"{'Записів':>12} | {'list O(n), с':>16} | {'dict O(1), с':>16}")
    print("-" * 52)
    for size in sizes:
        list_elapsed, dict_elapsed = benchmark_lookup(size)
        print(f"{size:>12,} | {list_elapsed:>16.8f} | {dict_elapsed:>16.8f}")
    print(
        "\nВисновок: лінійний пошук у списку перевіряє до n записів (O(n)); "
        "пошук за ключем у готовому словнику має середню складність O(1)."
    )


if __name__ == "__main__":
    run_benchmark()

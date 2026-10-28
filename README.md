# Car Catalog

Навчальний проєкт з дисципліни «Професійний Python», варіант 5 — каталог автомобілів. Проєкт зберігає інтерактивний каталог із ЛР1, додає структури даних і функціональну аналітику з ЛР2, lazy streaming pipeline з ЛР3, типізовану ООП-модель з ЛР4 та надійний імпорт/експорт із ЛР5.

## Вимоги

- Python 3.11+

## Встановлення

```bash
python -m venv .venv
```

Активуйте середовище (`.venv\Scripts\activate` у Windows або `source .venv/bin/activate` у Linux/macOS), потім встановіть проєкт і залежність для тестування:

```bash
python -m pip install -e ".[test]"
```

Для статичної перевірки типів ЛР4 встановіть також dev-залежності:

```bash
python -m pip install -e ".[dev]"
python -m mypy
```

Щоб відтворити звіт ЛР5 з актуальними результатами тестів, mypy та benchmark:

```bash
python -m pip install -e ".[test,dev,report]"
python scripts/build_lab5_report.py
```

Файл звіту створюється в `report/Горин_Михайло_Лаб05_V5.docx`.

## Запуск

Запустіть інтерактивний каталог:

```bash
python -m car_catalog.main
```

Команди `car-catalog` та `car-catalog-lab3` встановлюються як CLI entry points. У меню команда 9 демонструє ЛР2, команда 10 запускає порівняння пошуку в `list` і `dict`, команда 11 демонструє streaming pipeline ЛР3, команда 12 запускає benchmark eager/lazy, команда 13 демонструє ООП-модель ЛР4; команда 8 завершує застосунок.

Окремий запуск демонстрації ООП-моделі:

```bash
python -m car_catalog.oop_demo
```

Окремий запуск benchmark:

```bash
python -m car_catalog.benchmark
```

Benchmark вимірює пошук останнього запису для 1 000, 10 000 та 100 000 автомобілів. Побудова індексу не входить у час пошуку: сканування списку має складність O(n), а пошук у готовому словнику — середню O(1).

## Можливості ЛР2

- `processors`: `set`/`list`/`dict` comprehensions, індекс за порядковими ID, `Counter` та `defaultdict` групування.
- `analytics`: closure-фільтри, універсальна фільтрація, сортування через `lambda`, `*args`, `**kwargs` і агрегація.
- `decorators`: вимірювання часу та параметризований `@repeat`.
- `main`: інтерактивний режим ЛР1 і демонстраційний режим із обмеженою історією `deque`.

Основні складності: фільтрація/групування/підрахунок — O(n), побудова індексу — O(n), пошук у готовому `dict` — середня O(1), сортування — O(n log n).

## Лабораторна робота №3: ітератори, генератори та streaming

Вхідні CSV-записи мають формат `id,brand,model,year,price,mileage`; приклад із коректними й навмисно некоректним рядком є у [data/cars.csv](./data/cars.csv). Код розбитий за етапами в `car_catalog.streaming`:

```text
CSV file(s) → read_lines → clean_lines → parse_csv_rows
           → validate_car_rows → filter_cars → summarize_cars
           → batching / streaming aggregation → result
```

- Власний `CarIdIterator`, генератори з `yield`, `yield from`, рекурсивне розгортання та обмежений через `islice` нескінченний ID-потік.
- Ліниве читання одного чи кількох CSV-файлів через `itertools.chain`; валідація рахує некоректні рядки за категоріями.
- Фільтр за маркою/роком, lazy пошук за ID, перші N збігів із раннім завершенням, lazy трансформація та batching на `islice`.
- Однопрохідні середнє, найдорожче авто, мінімальний пробіг і підрахунки марок; додатково `itertools.accumulate`, `pairwise` та `groupby`.
- Групування через `groupby` попередньо сортує записи, тому саме цей додатковий етап матеріалізує дані й має O(n) пам’яті; звичайний pipeline та агрегування залишаються потоковими.

Запуск демонстрації та окремого benchmark:

```bash
python -m car_catalog.streaming
python -m car_catalog.streaming.benchmark
```

Benchmark автоматично генерує щонайменше 100 000 валідних записів і некоректні контрольні рядки у тимчасовому файлі, порівнює однакові eager/lazy результати, час обробки, час до першого запису та peak memory (`tracemalloc`). Файл тестових даних після запуску видаляється разом із тимчасовою директорією.

## Лабораторна робота №5: надійний імпорт та експорт

Модуль `car_catalog.reliable` імпортує каталог автомобілів із CSV у потоковому режимі, перевіряє кожний запис і експортує лише коректні записи до JSON. Політика `tolerant` реєструє некоректні рядки та продовжує роботу, а `strict` завершує імпорт при першій помилці. Конфігурація в [config/lab5.yaml](./config/lab5.yaml) задає шляхи, діапазони років і цін, політику та файл журналу; CLI приймає альтернативний шлях через змінну середовища `CAR_CATALOG_CONFIG`.

```bash
python -m car_catalog.reliable.main
python -m car_catalog.reliable.benchmark
```

Шляхи конфігурації відносні до `config/lab5.yaml`. Вихідний JSON записується атомарно: файл замінюється лише після повного успішного запису. Логи та результат виконання є згенерованими файлами у `logs/` і `output/`. Benchmark генерує тимчасовий CSV на 100 000 записів, порівнює eager зі streaming за часом і піковим споживанням пам'яті та перевіряє однаковість результатів за SHA-256.

## Тестування

```bash
python -m pytest -v
```

Команда запускає `tests/unit/` і `tests/integration/`, показує statement та branch coverage у терміналі й створює HTML-звіт `htmlcov/index.html`. Повний suite завершується помилкою, якщо combined coverage нижче 80%. Для чистого встановлення: `python -m pip install -e ".[test]"`. Integration suite має маркер `integration` і містить сценарії з реальною файловою системою в `tmp_path`.

Unit suite має окремі модулі за компонентами: application/repository interactions, CLI, OOP models, analytics/processors, reliable configuration/validation та streaming primitives. Integration suite ізольовано перевіряє надійний CSV → JSON import/export і файловий streaming pipeline.

Fixtures не мають спільного змінюваного стану; конфігураційна session fixture — незмінний об'єкт. Тестова factory створює нові моделі. `monkeypatch` перевіряє CLI environment override, input і заміну функцій; Mock/AsyncMock перевіряють результати, взаємодії й failure paths. `VehicleCatalogService.add_async()` offload-ить блокувальний запис у worker thread.

Файлові integration tests використовують тимчасові CSV/YAML/JSON через `tmp_path`; мережеві залежності відсутні.

Для запуску одного тесту або частини suite з coverage-порогом, вимкненим для неповного набору:

```bash
python -m pytest tests/unit/test_services.py::test_calculate_average_price --cov-fail-under=0
python -m pytest -m integration --cov-fail-under=0
python -m pytest -m "not integration" --cov-fail-under=0
```

Для формування звіту ЛР06 разом із результатами актуального запуску tests, branch/statement coverage, HTML coverage fragment і 80 відповідями на контрольні запитання:

```bash
python -m pip install -e ".[test,report]"
python scripts/build_lab6_report.py
```

Скрипт створює DOCX та PDF у `report/`; для PDF потрібен Microsoft Word у Windows.

## Автор

Михайло Горин
ЛНУ ім. Івана Франка, 121 — Інженерія програмного забезпечення

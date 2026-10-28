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

## Лабораторна робота №9: паралельність та оптимізація

Модуль `car_catalog.analytics` генерує відтворювані синтетичні каталоги, рахує середню ціну, межі пробігу, популяційну дисперсію та стандартне відхилення цін, рейтинг вартості автомобіля і кількість записів за марками. `analyze_cars` є еталонною реалізацією на циклах Python, `analyze_cars_numpy` векторизує числові розрахунки, а `CachedCarAnalytics` кешує статистику марки і скидає кеш методом `replace_cars`.

`car_catalog.parallel` порівнює потоки та процеси, читає кілька CSV/JSON файлів потоками та демонструє втрату конкурентних оновлень без блокування і коректний результат із `threading.Lock`. `car_catalog.profiling_tools` надає функції профілювання `cProfile` (включно з `ncalls`, `tottime`, `cumtime`) і вимірювання Python-алокацій через `tracemalloc`.

Встановлення, запуск тестів та типовий повний benchmark:

```powershell
python -m pip install -e ".[test]"
python -m pytest tests/test_parallel.py
python benchmarks/run_benchmarks.py
python -m car_catalog.profiling_tools
```

Для швидкої перевірки можна обмежити датасет і workers, не змінюючи набір показників:

```powershell
python benchmarks/run_benchmarks.py --sizes 10000 --workers 1 2 --repeats 2 --csv lab9-results.csv
```

За замовчуванням benchmark виконує п'ять вимірювань кожної комбінації на 10 000, 100 000 і 200 000 записах та виводить середній час, пікові Python-алокації й прискорення `Sp = T1 / Tp`. Для чистішого порівняння `tracemalloc` запускається окремо від часових вимірювань. Показник peak memory охоплює процес-ініціатор і не включає пам'ять дочірніх процесів у `ProcessPoolExecutor`.

Потоки не дають очікуваного прискорення CPU-bound Python-циклів: GIL дозволяє виконувати байткод Python лише одному потоку за раз в межах інтерпретатора. `ProcessPoolExecutor` обходить це обмеження окремими інтерпретаторами та ядрами, проте серіалізація, передавання даних, створення процесів і злиття часткових результатів створюють накладні витрати; на малих наборах вони можуть переважити виграш. NumPy виконує векторні обчислення у нативному коді та зменшує Python overhead, але побудова масивів теж має вартість. Тому заміряйте конкретний розмір та обладнання замість припускати лінійне масштабування.


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

## Лабораторна робота №7: SQLite persistence layer

Міграція `0003_country_nullable_vin` додає `manufacturers.country` (для наявних рядків заповнює `Unknown`) і дозволяє NULL у `cars.vin`; нові репозиторні записи виробників за замовчуванням також отримують країну `Unknown`.

Пакет `car_catalog.persistence` додає SQLite persistence layer до каталогу: SQLAlchemy-моделі `ManufacturerRecord` і `CarRecord` мають зв'язок one-to-many, первинні та зовнішній ключі, обмеження значень і унікальний VIN. `ManufacturerRepository` та `CarRepository` реалізують CRUD; репозиторій авто також підтримує пошук виробника, фільтр року, найдорожче авто, середню ціну та мінімальний пробіг. `CarCatalogService.update_prices_for_manufacturer()` змінює кілька цін в одній транзакції: помилка валідації чи належності авто відкочує всі зміни.

Щоб застосувати Alembic-міграції до SQLite-файлу за замовчуванням:

```bash
python -m pip install -e ".[test,dev]"
python -m alembic upgrade head
```

Запустіть інтерактивний каталог, який читає та змінює дані в SQLite:

```bash
python -m car_catalog.persistence.main
```

Або після встановлення проєкту запустіть entry point `car-catalog-lab7`. CLI створює схему для нової бази та надає перегляд, пошук за маркою, фільтр року, агрегати, CRUD автомобілів і масову зміну цін. Пункт 11 виконує JOIN/GROUP BY і показує COUNT, AVG, MAX та SUM за кожним виробником. Кожна операція використовує окрему SQLAlchemy-сесію; масове оновлення виконується атомарно.

Для окремої бази задайте URL в `CAR_CATALOG_DATABASE_URL` (наприклад, `sqlite:///data/catalog.db`) перед міграцією та запуском застосунку. Перша міграція створює таблиці `manufacturers` і `cars`; наступна додає обов'язковий унікальний VIN та заповнює його для вже наявних записів. `Database.create_schema()` зручний для нової БД і тестів; для оновлення існуючої БД використовуйте Alembic.

Міграції підтримують і прямий, і зворотний перехід. `downgrade -1` відкочує останню міграцію; `downgrade base` видаляє всі таблиці застосунку та їхні дані, тому виконуйте повний downgrade лише для тестової/резервованої бази:

```bash
python -m alembic downgrade -1
python -m alembic upgrade head

# Повний відкат схеми, потім повторне створення
python -m alembic downgrade base
python -m alembic upgrade head
```

Для перевірки реальної SQLite-схеми після `upgrade head` виконайте команди нижче. `.tables` і `.schema` — команди інтерактивного `sqlite3`; `PRAGMA table_info` показує стовпці, типи та `NOT NULL`:

```text
sqlite3 car_catalog.db
sqlite> .tables
alembic_version  cars             manufacturers
sqlite> .schema cars
CREATE TABLE IF NOT EXISTS "cars" (
    id INTEGER NOT NULL,
    manufacturer_id INTEGER NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    price FLOAT NOT NULL,
    mileage INTEGER NOT NULL,
    vin VARCHAR(32),
    PRIMARY KEY (id),
    CONSTRAINT fk_cars_manufacturer_id_manufacturers FOREIGN KEY(manufacturer_id) REFERENCES manufacturers (id) ON DELETE CASCADE,
    CONSTRAINT ck_cars_year CHECK (year >= 1886),
    CONSTRAINT ck_cars_price CHECK (price >= 0),
    CONSTRAINT ck_cars_model CHECK (length(trim(model)) > 0),
    CONSTRAINT ck_cars_mileage CHECK (mileage >= 0),
    CONSTRAINT uq_cars_vin UNIQUE (vin)
);
CREATE INDEX ix_cars_manufacturer_year ON cars (manufacturer_id, year);
sqlite> PRAGMA table_info(cars);
0|id|INTEGER|1||1
1|manufacturer_id|INTEGER|1||0
2|model|VARCHAR(100)|1||0
3|year|INTEGER|1||0
4|price|FLOAT|1||0
5|mileage|INTEGER|1||0
6|vin|VARCHAR(32)|0||0
sqlite> .quit
```

Репозиторії приймають SQLAlchemy `Session`; керуйте їх записами через `with database.session_factory.begin() as session:` — успішний блок виконує commit, виняток автоматично викликає rollback. `search_cars_by_manufacturer()` окремо демонструє параметризований SQLite DB-API запит. Транзакційність забезпечує атомарність і довговічність після commit, обмеження та зовнішні ключі — узгодженість, а ізоляція транзакцій залежить від режиму SQLite та рівня блокування.

Integration tests використовують окремі тимчасові SQLite-файли, перевіряють CRUD, окремі зміни ціни та пробігу, зв'язок виробник–авто, пошук/агрегати, UNIQUE та CHECK constraints, DB-API запит, commit/rollback, перехід міграції зі старої схеми та downgrade/upgrade.

## Лабораторна робота №8: REST API та асинхронні HTTP-запити

`car_catalog.api` надає FastAPI CRUD для автомобілів, пошук за моделлю/виробником, фільтри за роком і ціною, перелік авто виробника та статистику через наявний `CarCatalogDbService`. API використовує SQLAlchemy persistence layer із ЛР7 і Pydantic v2-схеми. Відповіді на помилкові запити мають HTTP-коди 404, 409 та 422; створення повертає 201, видалення — 204.

Встановіть залежності API й тестів та запустіть сервер:

```powershell
python -m pip install -e ".[test]"
python -m alembic upgrade head
python -m uvicorn car_catalog.api:app --reload
```

Для `POST /cars/batch-check` задайте URL довіреного зовнішнього сервісу у `CAR_CATALOG_EXTERNAL_API_URL`. Endpoint приймає до 100 додатних ID, перевіряє записи паралельно з обмеженням конкурентності, таймаутом і повторними спробами з експоненційною затримкою. Якщо інтеграцію не налаштовано, endpoint повертає 503 замість удаваного успіху.

Запустіть інтеграційні API-тести та весь набір:

```powershell
python -m pytest tests/test_api.py -v
python -m pytest -v
```

## Тестування

```bash
python -m pytest -v
```

Команда запускає тести з `tests/`, показує statement та branch coverage у терміналі й створює HTML-звіт `htmlcov/index.html`. Повний suite завершується помилкою, якщо combined coverage нижче 80%. Для чистого встановлення: `python -m pip install -e ".[test]"`. Integration suite має маркер `integration` і містить сценарії з реальною файловою системою в `tmp_path`.

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

## Production: ЛР10

ЛР10 пакує проєкт `car-catalog` як wheel і source distribution, запускає наявний FastAPI-каталог через CLI, читає конфігурацію з оточення та постачає Docker-образ і GitHub Actions CI. Проєкт підтримує Python 3.11+, а CI і контейнер збираються на Python 3.12.

### Конфігурація

Налаштування завантажуються через `pydantic-settings` із змінних оточення та, для локальної розробки, із `.env`. Скопіюйте шаблон і за потреби змініть значення:

```powershell
Copy-Item .env.example .env
```

| Змінна | Значення за замовчуванням | Призначення |
|---|---|---|
| `DATABASE_URL` | `sqlite:///car_catalog.db` | SQLAlchemy URL бази даних; абсолютний шлях SQLite підтримується |
| `ENVIRONMENT` | `development` | Назва оточення, яку повертає `/health` |
| `LOG_LEVEL` | `INFO` | Рівень структурованого JSON-логування |
| `HOST` | `0.0.0.0` | Адреса HTTP-сервера |
| `PORT` | `8000` | Порт HTTP-сервера (1–65535) |
| `EXTERNAL_API_URL` | не задано | Необов'язкова абсолютна HTTP(S)-адреса для `/cars/batch-check` |

Також підтримуються імена `CAR_CATALOG_DATABASE_URL`, `CAR_CATALOG_ENVIRONMENT`, `CAR_CATALOG_LOG_LEVEL`, `CAR_CATALOG_HOST`, `CAR_CATALOG_PORT` і `CAR_CATALOG_EXTERNAL_API_URL`. Не зберігайте реальні паролі, токени або приватні URL у репозиторії: `.env` ігнорується Git та Docker.

### Локальний запуск API

```powershell
python -m pip install -e ".[dev,test]"
car-catalog
```

Або запустіть CLI без інсталяції пакета після активації середовища:

```powershell
python -m car_catalog.main
```

API та інтерактивна документація доступні за адресами `http://127.0.0.1:8000`, `/docs` та `/redoc`. CLI `car-catalog` запускає HTTP API; інтерактивну демонстрацію каталогу можна запустити з Python через `car_catalog.main.run_demo()`.

### REST API

| Метод | Шлях | Призначення |
|---|---|---|
| `GET` | `/health` | Статус процесу та назва середовища |
| `GET` | `/cars` | Список автомобілів із пошуком і фільтрами |
| `POST` | `/cars` | Додавання автомобіля |
| `GET` | `/cars/{car_id}` | Отримання автомобіля |
| `PATCH` | `/cars/{car_id}` | Оновлення ціни та/або пробігу |
| `DELETE` | `/cars/{car_id}` | Видалення автомобіля |
| `GET` | `/manufacturers/{manufacturer_id}/cars` | Автомобілі виробника |
| `GET` | `/cars/statistics/summary` | Зведена статистика каталогу |
| `GET` | `/cars/statistics` | Сумісний короткий маршрут статистики |
| `POST` | `/cars/batch-check` | Асинхронна перевірка зовнішніх ідентифікаторів; потребує `EXTERNAL_API_URL` |

### Тести та перевірки якості

Встановлення тестових і статичних інструментів, а також команди, які виконує CI:

```powershell
python -m pip install -e ".[dev,test]"
ruff check .
ruff format --check `
  src/car_catalog/api.py `
  src/car_catalog/config.py `
  src/car_catalog/dependencies.py `
  src/car_catalog/logging_config.py `
  src/car_catalog/main.py `
  src/car_catalog/persistence/database.py `
  src/car_catalog/streaming/pipeline.py `
  tests/test_api.py `
  tests/test_config.py
mypy
pytest
```

CI перевіряє форматування всіх production-related Python-файлів, змінених у ЛР10. Pytest налаштований на branch coverage та звіти в терміналі й `htmlcov`; мінімальне покриття задається в `pyproject.toml`.

### Збірка пакета

```powershell
python -m pip install build
python -m build
Get-ChildItem dist
python -m pip install --force-reinstall (Get-ChildItem dist\car_catalog-1.0.0-py3-none-any.whl).FullName
car-catalog
```

Команда `python -m build` створює wheel і sdist у `dist/`. Перевірка встановлення wheel запускає встановлену консольну точку входу; для ізоляції використовуйте окреме віртуальне середовище.

### Docker

Multi-stage Dockerfile використовує `python:3.12-slim`, запускає процес від непривілейованого `appuser` та перевіряє `/health`. SQLite-файл у контейнері розташований у `/app/data/car_catalog.db`; підключайте named volume для збереження даних між перезапусками:

```powershell
docker build -t car-catalog:1.0.0 .
docker volume create car_data
docker run -d --name car-catalog `
  -p 8000:8000 `
  -v car_data:/app/data `
  -e DATABASE_URL=sqlite:////app/data/car_catalog.db `
  -e ENVIRONMENT=production `
  -e LOG_LEVEL=INFO `
  car-catalog:1.0.0
curl.exe http://localhost:8000/health
docker logs car-catalog
docker stop car-catalog
docker rm car-catalog
```

На Linux/macOS ті самі параметри `docker run` можна записати в один рядок. Якщо використовуєте `--env-file`, перевірте, що `DATABASE_URL` вказує саме на `/app/data/car_catalog.db`, а `HOST` — на `0.0.0.0`. Не монтуйте `.env` у контейнер.

### CI/CD та реліз

Workflow `.github/workflows/ci.yml` запускається на push у `main`/`master` і pull request. Послідовні кроки: checkout, Python 3.12, встановлення залежностей, Ruff lint і format check, strict mypy за списком модулів у конфігурації, pytest із покриттям, збірка wheel/sdist та Docker image. Публікація образу чи пакета навмисно не виконується автоматично; для неї налаштуйте окремий релізний workflow і мінімальні потрібні секрети середовища.

### Production checklist

- [ ] Конфігурація середовища перевірена; у Git немає `.env`, паролів, токенів або приватних адрес.
- [ ] Ruff, mypy та весь pytest-набір проходять, а покриття відповідає порогу з `pyproject.toml`.
- [ ] Wheel і sdist зібрані, wheel встановлюється та надає команду `car-catalog`.
- [ ] Docker-образ використовує `appuser`; `docker inspect` показує успішний healthcheck.
- [ ] SQLite розташована на named volume `car_data:/app/data`; перевірено збереження після перезапуску контейнера.
- [ ] `/health` повертає `{"status":"ok","environment":"production"}`; логи мають JSON-формат.
- [ ] У CI успішно пройшли тести, побудова пакетів і Docker image; теги та нотатки релізу узгоджені з версією.

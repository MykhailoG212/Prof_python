# Car Catalog

Консольний застосунок для обліку та аналізу бази даних автомобілів. Створено в межах курсу «Професійний Python» (Лабораторна робота №1, Варіант 5).

## Вимоги
- Python 3.11+

## Встановлення та розгортання
1. Створення та активація віртуального середовища:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```
2. Встановлення пакета в режимі розробки разом із тестовими залежностями:
   ```bash
   python -m pip install -e ".[test]"
   ```

## Запуск застосунку
Запуск як модуль:

```bash
python -m car_catalog.main
```

Або через CLI скрипт:

```bash
car-catalog
```

## Тестування

```bash
python -m pytest
```

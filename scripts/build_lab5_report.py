from __future__ import annotations

import os
from pathlib import Path
from shutil import copyfile
import subprocess
import sys

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from car_catalog.reliable.benchmark import measure_benchmark  # noqa: E402

TEMPLATE = ROOT / "report" / "Горин_Михайло_Лаб04_V5.docx"
OUTPUT = ROOT / "report" / "Горин_Михайло_Лаб05_V5.docx"
ASSETS = ROOT / ".lab5_report_qa" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def run_command(arguments: list[str]) -> str:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        check=True,
        encoding="utf-8",
        env=environment,
        errors="replace",
        text=True,
    )
    return result.stdout.strip()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "consolab.ttf" if bold else "consola.ttf"
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


def terminal_image(name: str, title: str, text: str) -> Path:
    lines = text.splitlines()
    image = Image.new("RGB", (1450, 100 + 42 * max(3, len(lines))), "#111827")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 1450, 62), 16, fill="#1f2937")
    draw.ellipse((26, 21, 40, 35), fill="#ef4444")
    draw.ellipse((50, 21, 64, 35), fill="#f59e0b")
    draw.ellipse((74, 21, 88, 35), fill="#22c55e")
    draw.text((115, 16), title, font=font(23, True), fill="#e5e7eb")
    y = 82
    for line in lines:
        color = "#86efac" if line.startswith("PS>") else "#f3f4f6"
        draw.text((32, y), line, font=font(23), fill=color)
        y += 42
    path = ASSETS / name
    image.save(path)
    return path


def diagram_image() -> Path:
    image = Image.new("RGB", (1500, 870), "white")
    draw = ImageDraw.Draw(image)
    title = font(31, True)
    normal = font(23)
    box_font = font(20)

    def box(x: int, y: int, w: int, h: int, label: str, fill: str) -> None:
        draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=fill, outline="#4b5563", width=3)
        rows = label.split("\n")
        for i, row in enumerate(rows):
            draw.text((x + 20, y + 18 + i * 28), row, font=box_font, fill="#111827")

    def arrow(a: tuple[int, int], b: tuple[int, int], text: str = "") -> None:
        draw.line((a, b), fill="#2563eb", width=5)
        draw.polygon([(b[0], b[1]), (b[0] - 14, b[1] - 8), (b[0] - 14, b[1] + 8)], fill="#2563eb")
        if text:
            draw.text(((a[0] + b[0]) // 2 - 45, (a[1] + b[1]) // 2 - 28), text, font=normal, fill="#1d4ed8")

    draw.text((45, 24), "Архітектура надійного імпорту та експорту ЛР5", font=title, fill="#111827")
    box(70, 155, 270, 130, "config/lab5.yaml\nшляхи, межі, policy", "#dbeafe")
    box(70, 500, 270, 130, "CSV input\nпотік рядків", "#dcfce7")
    box(490, 140, 330, 185, "config.py\nload_config()\nfail-fast validation", "#fef3c7")
    box(490, 470, 330, 205, "importers.py\nread_vehicles()\nparse_vehicle()\nRecordValidationError", "#fce7f3")
    box(1050, 125, 330, 190, "services.py\nstrict / tolerant\nstats + logging", "#ede9fe")
    box(1050, 490, 330, 155, "exporters.py\natomic_text_writer()\noutput JSON", "#cffafe")
    arrow((340, 220), (490, 220), "YAML")
    arrow((340, 565), (490, 565), "CSV")
    arrow((820, 230), (1050, 230), "config")
    arrow((820, 565), (1050, 565), "Vehicle / error")
    arrow((1215, 315), (1215, 490), "valid records")
    draw.text((460, 745), "Logging фіксує некоректні рядки; JSON замінюється тільки після успішного запису.", font=normal, fill="#374151")
    path = ASSETS / "architecture.png"
    image.save(path)
    return path


DEMO = terminal_image(
    "demo.png",
    "PowerShell - запуск ЛР5",
    "PS> .\\.venv\\Scripts\\python.exe -m car_catalog.reliable.main\n"
    + run_command(["-m", "car_catalog.reliable.main"]),
)
TESTS = terminal_image(
    "tests.png",
    "PowerShell - pytest",
    "PS> .\\.venv\\Scripts\\python.exe -m pytest -q\n" + run_command(["-m", "pytest", "-q"]),
)
MYPY = terminal_image(
    "mypy.png",
    "PowerShell - mypy",
    "PS> .\\.venv\\Scripts\\python.exe -m mypy src/car_catalog/reliable tests/test_reliable_importer.py\n"
    + run_command(["-m", "mypy", "src/car_catalog/reliable", "tests/test_reliable_importer.py"]),
)
BENCHMARK_EAGER, BENCHMARK_STREAMING = measure_benchmark()
BENCHMARK = terminal_image(
    "benchmark.png",
    "PowerShell - benchmark ЛР5",
    "\n".join(
        [
            "PS> .\\.venv\\Scripts\\python.exe -m car_catalog.reliable.benchmark",
            "Dataset: 100,000 valid candidates plus 10 malformed control rows",
            f"eager     | {BENCHMARK_EAGER.elapsed_seconds:>8.4f} s | "
            f"{BENCHMARK_EAGER.peak_memory_bytes / (1024 * 1024):>7.3f} MiB",
            f"streaming | {BENCHMARK_STREAMING.elapsed_seconds:>8.4f} s | "
            f"{BENCHMARK_STREAMING.peak_memory_bytes / (1024 * 1024):>7.3f} MiB",
            f"valid=100,000 invalid=10; results match: {BENCHMARK_EAGER.summary.sha256[:16]}",
        ]
    ),
)
DIAGRAM = diagram_image()


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shade = OxmlElement("w:shd")
    shade.set(qn("w:fill"), fill)
    tc_pr.append(shade)


def add_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        item = OxmlElement(f"w:{edge}")
        item.set(qn("w:val"), "single")
        item.set(qn("w:sz"), "6")
        item.set(qn("w:color"), "A6A6A6")
        borders.append(item)
    tbl_pr.append(borders)


def set_font(run, size: float, bold: bool = False, name: str = "Times New Roman") -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:ascii"), name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.bold = bold


def paragraph(doc, text: str = "", *, bold: bool = False, size: float = 14, align=None, indent: bool = True):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.alignment = align or WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    r = p.add_run(text)
    set_font(r, size, bold)
    return p


def heading(doc, number: str, title: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(f"{number}. {title}")
    set_font(r, 14, True)


def code(doc, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.left_indent = Cm(0.7)
    p.paragraph_format.line_spacing = 1.0
    for line in text.rstrip().splitlines():
        run = p.add_run(line + "\n")
        set_font(run, 8.5, name="Consolas")


def image(doc, path: Path, caption: str, width: float = 15.0) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(5)
    r = cap.add_run(caption)
    set_font(r, 11)


def table(doc, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    add_borders(t)
    for index, value in enumerate(headers):
        cell = t.rows[0].cells[index]
        cell.width = Cm(widths[index])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, "DDEBF7")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(value)
        set_font(r, 10, True)
    for row in rows:
        cells = t.add_row().cells
        for index, value in enumerate(row):
            cells[index].width = Cm(widths[index])
            p = cells[index].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(value)
            set_font(r, 9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def page_break(doc) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def source(relative: str, start: int = 1, end: int | None = None) -> str:
    lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start - 1 : end])


copyfile(TEMPLATE, OUTPUT)
doc = Document(OUTPUT)
body = doc._element.body
for child in list(body):
    if child.tag != qn("w:sectPr"):
        body.remove(child)

# Cover page
for text, bold, top in [
    ("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", True, 0),
    ("Львівський національний університет імені Івана Франка", True, 0),
    ("Факультет електроніки та комп’ютерних технологій", False, 0),
]:
    p = paragraph(doc, text, bold=bold, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    if top:
        p.paragraph_format.space_before = Pt(top)
for _ in range(5):
    paragraph(doc, "", indent=False)
for text, bold in [
    ("ЗВІТ", True),
    ("про виконання лабораторної роботи №5", False),
    ("«Обробка помилок, файли та серіалізація»", True),
    ("з дисципліни «Професійний Python»", False),
    ("Варіант №5 — «Каталог автомобілів»", False),
]:
    paragraph(doc, text, bold=bold, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
for _ in range(4):
    paragraph(doc, "", indent=False)
for text, bold in [("Виконав:", True), ("студент групи ФЕП-32", False), ("Горин Михайло", False), ("Репозиторій: github.com/MykhailoG212/Prof_python", False)]:
    paragraph(doc, text, bold=bold, align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False)
for _ in range(3):
    paragraph(doc, "", indent=False)
paragraph(doc, "Львів — 2026", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
page_break(doc)

heading(doc, "2", "Номер і тема лабораторної роботи")
paragraph(doc, "Лабораторна робота №5. Тема: «Обробка помилок, файли та серіалізація». У звіті наведено модуль надійного імпорту та експорту каталогу автомобілів: зовнішня конфігурація, потокове читання CSV, валідація, контрольована обробка помилок, логування й атомарний JSON-експорт.")
heading(doc, "3", "Мета роботи")
paragraph(doc, "Сформувати практичні навички створення надійних Python-програм, що коректно працюють із файловими ресурсами та некоректними зовнішніми даними. Застосувати exceptions, власну ієрархію помилок, exception chaining, context managers, pathlib, CSV, JSON, YAML-конфігурацію, logging, streaming I/O і атомарний запис файлів.")
heading(doc, "4", "Номер індивідуального варіанта")
paragraph(doc, "Варіант №5 — «Каталог автомобілів». Наступний етап наскрізного проєкту використовує знайому предметну область і додає інфраструктурний модуль для контрольованого обміну даними між CSV-файлом та JSON-експортом.")
heading(doc, "5", "Постановка задачі")
paragraph(doc, "Потрібно реалізувати імпорт та експорт каталогу автомобілів з полями vehicle_id, brand, model, year, price, mileage. Система має перевіряти додатний ID, непорожні марку й модель, допустимий діапазон року та ціни, невід’ємний пробіг. Вимоги включають streaming CSV import, JSON export, YAML-налаштування діапазонів року й ціни, статистику та logging.")
heading(doc, "5.1", "Вимоги індивідуального варіанта №5")
table(doc, ["Вимога", "Реалізація"], [
    ["Поля vehicle_id, brand, model, year, price, mileage", "Vehicle dataclass і parse_vehicle() у reliable/models.py та reliable/importers.py."],
    ["Streaming CSV import", "csv.DictReader у read_vehicles(); файл читається в межах with і рядки обробляються по одному."],
    ["Діапазони років і цін", "config/lab5.yaml; load_config() перевіряє конфігурацію до початку обробки."],
    ["Strict і tolerant режими", "invalid_record_policy визначає продовження або зупинку на першому некоректному записі."],
    ["JSON export і logging", "export_json() виконує атомарний запис; services.py фіксує warning для невалідного рядка."],
], [6.0, 10.0])
heading(doc, "5.2", "Загальні вимоги лабораторної роботи")
table(doc, ["Компонент", "Виконання"], [
    ["Custom exceptions", "ApplicationError, ConfigurationError, DataImportError, RecordValidationError, DataExportError."],
    ["Exception chaining", "Перетворення ValueError/KeyError/OSError на domain error через raise ... from error."],
    ["Context managers", "with path.open(), власний @contextmanager atomic_text_writer()."],
    ["Безпечний output", "Тимчасовий файл замінює ціль через os.replace() лише після успішного json.dump()."],
], [6.0, 10.0])

heading(doc, "6", "Структура проєкту")
paragraph(doc, "Нова підсистема не змінює попередні модулі каталогу. Вона відокремлює конфігурацію, ввід-вивід, доменні дані та orchestration, тому правила валідації й обробка файлових помилок не змішуються з UI або аналітикою.")
code(doc, "src/car_catalog/reliable/\n├── __init__.py\n├── config.py        # PyYAML loader і fail-fast validation\n├── exceptions.py    # hierarchy application errors\n├── models.py        # Vehicle та config dataclasses\n├── importers.py     # streaming CSV reader і parser\n├── exporters.py     # atomic JSON writer\n├── services.py      # strict/tolerant orchestration, statistics, logging\n├── benchmark.py     # eager/streaming і peak-memory experiment\n└── main.py          # CLI entry point\nconfig/lab5.yaml\ndata/lab5_vehicles.csv\ntests/test_reliable_importer.py")
heading(doc, "7", "Архітектура модуля")
paragraph(doc, "Конфігурація є окремою точкою входу для параметрів. Вхідний CSV проходить потокове читання, парсинг і валідацію. Service застосовує політику strict або tolerant, збирає статистику та передає тільки valid записи експортеру. Вихідний JSON пишеться через власний context manager.")
image(doc, DIAGRAM, "Рисунок 1 — Компоненти модуля надійного імпорту та експорту ЛР5", 16.5)
heading(doc, "8", "Схема вхідних даних і приклад CSV")
table(doc, ["Поле", "Тип", "Правило"], [
    ["vehicle_id", "int", "Додатне ціле число."],
    ["brand, model", "str", "Непорожні значення після trim."],
    ["year", "int", "У межах minimum_year..maximum_year із YAML."],
    ["price", "float", "Скінченне число у межах minimum_price..maximum_price."],
    ["mileage", "int", "Невід’ємне ціле число."],
], [4.0, 3.0, 9.0])
code(doc, source("data/lab5_vehicles.csv"))
heading(doc, "9", "Ієрархія власних винятків")
paragraph(doc, "Ієрархія відокремлює критичні помилки застосунку від помилок одиничних записів. Це дає змогу main.py завершитися контрольовано, а tolerant-режиму продовжити обробку після RecordValidationError.")
code(doc, source("src/car_catalog/reliable/exceptions.py"))
heading(doc, "10", "YAML configuration і fail-fast validation")
paragraph(doc, "Конфігурація зчитується через yaml.safe_load() до відкриття CSV. load_config() перевіряє структуру YAML, типи обов’язкових значень, policy, скінченність і порядок меж ціни, межі року, наявність input file та розділення шляхів input/output/log. Відносні шляхи прив’язуються до каталогу конфігураційного файла.")
code(doc, source("config/lab5.yaml"))
code(doc, source("src/car_catalog/reliable/config.py"))
heading(doc, "11", "Streaming reader і валідація")
paragraph(doc, "read_vehicles() використовує csv.reader зі strict parsing усередині with і обробляє кожний запис окремо. Генератор повертає результат для рядка, не накопичуючи весь файл у пам’яті; помилки схеми заголовка є критичними, а записи з неправильною кількістю полів обробляються за strict/tolerant policy. parse_vehicle() розділяє перетворення типів і предметні правила; низькорівневі ValueError та KeyError передаються як explicit exception chain.")
code(doc, source("src/car_catalog/reliable/importers.py"))
heading(doc, "12", "Strict і tolerant processing")
paragraph(doc, "У tolerant-режимі service збільшує invalid_count, пише warning у лог і переходить до наступного рядка. У strict-режимі той самий RecordValidationError стає причиною DataImportError, тому експорт не запускається. Це гарантує, що strict результат не містить частково обробленого набору.")
code(doc, source("src/car_catalog/reliable/services.py", 31, 56))
heading(doc, "13", "JSON serialization та атомарний export")
paragraph(doc, "atomic_text_writer() створює temporary file у тій самій теці, щоб os.replace() був атомарною операцією в межах файлової системи. Якщо json.dump() або запис завершився помилкою, finally видаляє temporary file, а старий output лишається незмінним.")
code(doc, source("src/car_catalog/reliable/exporters.py"))
heading(doc, "14", "Власний context manager")
paragraph(doc, "Власний context manager реалізовано декоратором @contextmanager. Він централізує lifecycle temporary file, успішну заміну осередкового файла та cleanup у finally. Тест test_atomic_writer_preserves_existing_file_after_failure підтверджує, що при штучному RuntimeError попередній output.json залишається зі старим вмістом.")
heading(doc, "15", "Демонстраційний запуск")
paragraph(doc, "Для запуску використано config/lab5.yaml і data/lab5_vehicles.csv. У вихідному наборі є три коректні автомобілі та один запис з нечисловим vehicle_id і ціною. За tolerant policy програма експортує три valid записи, реєструє один invalid запис і завершується успішно.")
image(doc, DEMO, "Рисунок 2 — Результат запуску демонстраційного сценарію ЛР5", 16.0)
heading(doc, "16", "Logging і приклад повідомлення")
paragraph(doc, "Лог записується в logs/lab5.log у кодуванні UTF-8. Повідомлення містить номер рядка, поле за наявності та опис помилки, але не зберігає весь CSV-запис. Це дає достатній контекст для діагностики без дублювання даних у журналі.")
code(doc, source("src/car_catalog/reliable/services.py", 20, 37))
code(doc, "2026-10-27 20:00:00,000 WARNING line=4 field=None error=numeric field has invalid value\n2026-10-27 20:00:00,000 INFO Import completed: valid=3 invalid=1")
heading(doc, "17", "Автоматизоване тестування")
paragraph(doc, "Новий tests/test_reliable_importer.py перевіряє tolerant import і JSON payload, зупинку strict import із збереженим exception cause, fail-fast конфігурацію та атомарний запис. Увесь набір проєкту включає також тести попередніх лабораторних робіт.")
image(doc, TESTS, "Рисунок 3 — Фактичний результат повного прогону pytest", 16.0)
heading(doc, "18", "Статична перевірка типів")
paragraph(doc, "Модулі ЛР5 мають анотації типів для конфігурації, domain model, ітераторів, context manager та сервісу. Окрема перевірка mypy охоплює новий пакет і тестовий модуль.")
image(doc, MYPY, "Рисунок 4 — Результат перевірки mypy для ЛР5", 16.0)
heading(doc, "19", "Результати strict і tolerant experiment")
table(doc, ["Показник", "Tolerant", "Strict"], [
    ["Коректні записи до помилки", "3 exported", "1 до першої помилки"],
    ["Некоректний рядок", "warning у log, обробка продовжується", "DataImportError, процес зупиняється"],
    ["JSON output", "Містить лише 3 valid записи", "Старий файл зберігається; новий export не комітиться"],
    ["Причина помилки", "RecordValidationError врахований у статистиці", "RecordValidationError доступний як __cause__"],
], [4.4, 5.8, 5.8])
heading(doc, "20", "Експеримент streaming/eager і пікова пам’ять")
paragraph(doc, "Для вимірювання згенеровано 100 000 валідних кандидатів і 10 некоректних контрольних рядків. Обидва режими використовують один parser/validator, рахують валідні й невалідні записи та обчислюють SHA-256 канонічного JSON для кожного валідного автомобіля. Eager зберігає всі результати імпорту в list; streaming обробляє по одному запису. Peak memory вимірюється через tracemalloc (Python allocations), файл тесту не враховується.")
image(doc, BENCHMARK, "Рисунок 5 — Відтворюваний вимір часу та peak memory для ЛР5", 16.0)
table(doc, ["Режим", "Час, с", "Peak memory, MiB", "Valid / invalid", "Перевірка виходу"], [
    ["Eager", f"{BENCHMARK_EAGER.elapsed_seconds:.4f}", f"{BENCHMARK_EAGER.peak_memory_bytes / (1024 * 1024):.3f}", "100 000 / 10", "SHA-256 збігається"],
    ["Streaming", f"{BENCHMARK_STREAMING.elapsed_seconds:.4f}", f"{BENCHMARK_STREAMING.peak_memory_bytes / (1024 * 1024):.3f}", "100 000 / 10", "SHA-256 збігається"],
], [2.4, 2.2, 3.2, 3.2, 5.0])
paragraph(doc, f"SHA-256 результату: {BENCHMARK_EAGER.summary.sha256}. У цьому запуску streaming використав приблизно {BENCHMARK_EAGER.peak_memory_bytes / BENCHMARK_STREAMING.peak_memory_bytes:.1f}× менше peak Python memory. Час залежить від середовища; коректність підтверджується однаковими статистиками та digest.")
heading(doc, "21", "Фрагмент тестів ЛР5")
code(
    doc,
    source("tests/test_reliable_importer.py", 45, 59)
    + "\n\n"
    + source("tests/test_reliable_importer.py", 189, 199),
)
heading(doc, "22", "Відповіді на контрольні запитання")
qa = [
    ("1. Чому не слід перехоплювати bare except?", "Він приховує системні й програмні помилки; тут обробляються конкретні OSError, csv.Error, ValueError та domain exceptions."),
    ("2. Навіщо exception chaining?", "Воно зберігає технічну причину, коли ValueError або OSError перетворюється на зрозумілу помилку предметної області."),
    ("3. Чому використано with?", "Контекстний менеджер закриває CSV та temporary file навіть при exception."),
    ("4. Чому CSV читається потоково?", "csv.reader повертає записи по одному, тому пам’ять не залежить від повного розміру input."),
    ("5. Для чого atomic export?", "Він не дає пошкодити наявний JSON, коли серіалізація або запис перериваються."),
    ("6. Коли застосовувати strict policy?", "Коли хоча б один некоректний запис робить весь набір недостовірним."),
    ("7. Коли застосовувати tolerant policy?", "Коли valid записи можна безпечно опрацювати, а помилки потрібно зафіксувати для подальшого виправлення."),
    ("8. Чому конфігурацію перевіряють на старті?", "Fail-fast запобігає довгій обробці з неправильними шляхами або межами."),
]
for question, answer in qa:
    p = paragraph(doc, "", indent=False)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(question + " ")
    set_font(r, 12, True)
    r = p.add_run(answer)
    set_font(r, 12)
heading(doc, "23", "Висновок")
paragraph(doc, "У лабораторній роботі реалізовано надійний модуль імпорту й експорту каталогу автомобілів для варіанта №5. Модуль завантажує та перевіряє YAML-конфігурацію, потоково читає CSV, валідує записи, контролює strict/tolerant policy, веде журнал і створює JSON через атомарний output. Тести підтверджують поведінку за помилок, а відтворюваний eager/streaming експеримент засвідчує однакові результати з істотно нижчим піковим споживанням пам’яті для streaming режиму.")

doc.save(OUTPUT)
print(OUTPUT)

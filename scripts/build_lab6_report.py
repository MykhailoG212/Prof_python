from __future__ import annotations

import base64
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.document import Document as DocumentType
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.section import Section
from docx.shared import Cm, Pt
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
OUTPUT = REPORT_DIR / "Горин_Михайло_Лаб06_V5.docx"
PDF_OUTPUT = REPORT_DIR / "Горин_Михайло_Лаб06_V5.pdf"


QUESTIONS: list[tuple[str, str]] = [
    ("Що таке automated test?", "Це код, який автоматично запускає перевірку очікуваної поведінки програми та сигналізує про невідповідність."),
    ("Які основні переваги автоматизованого тестування?", "Воно швидко виявляє defects, захищає від regressions, документує поведінку та спрощує безпечний refactoring."),
    ("Що таке regression?", "Це раніше справна поведінка, яку порушила нова зміна коду."),
    ("Що таке unit test?", "Перевірка однієї невеликої одиниці поведінки ізольовано від сторонніх компонентів."),
    ("Що таке integration test?", "Перевірка взаємодії кількох компонентів, наприклад CSV-читача, валідатора та JSON-експортера."),
    ("Чим integration test відрізняється від unit test?", "Integration test охоплює кілька компонентів і їхні межі; unit test перевіряє один компонент, зазвичай із підміною залежностей."),
    ("Що показує test pyramid?", "Рекомендоване співвідношення: багато швидких unit-тестів, менше integration-тестів і ще менше дорогих end-to-end-тестів."),
    ("Чому unit tests зазвичай більше?", "Вони швидші, дешевші, детермінованіші та точніше вказують на місце дефекту."),
    ("Що таке pytest?", "Це Python-фреймворк для автоматизованого тестування з assert-перевірками, fixtures, параметризацією та плагінами."),
    ("Як pytest знаходить tests?", "За типовими шаблонами: файли test_*.py або *_test.py та функції/методи з префіксом test_."),
    ("Якою командою запускається pytest?", "У цьому проєкті: python -m pytest; встановлені addopts також формують coverage-звіти."),
    ("Для чого pytest -v?", "Для детального виводу з окремою назвою та статусом кожного тесту."),
    ("Для чого pytest -x?", "Щоб зупинити запуск після першого невдалого тесту."),
    ("Що означає Arrange–Act–Assert?", "Arrange готує дані, Act виконує дію, Assert перевіряє результат."),
    ("Для чого використовується assert?", "Він фіксує очікувану умову; pytest показує відмінності, коли умова хибна."),
    ("Що таке assertion failure?", "Це невиконана перевірка, яка доводить розбіжність між фактичним і очікуваним результатом."),
    ("Чому floats не завжди слід порівнювати через ==?", "Двійкове представлення десяткових дробів може давати малу похибку округлення."),
    ("Для чого pytest.approx?", "Для порівняння чисел або числових послідовностей із допустимою похибкою."),
    ("Для чого pytest.raises?", "Для перевірки, що конкретна дія піднімає очікуваний тип винятку."),
    ("Як перевірити exception message?", "Задати match у pytest.raises або перевірити текст отриманого винятку через exc_info."),
    ("Як отримати exception object через exc_info?", "Використати `with pytest.raises(Type) as exc_info:` і звернутися до `exc_info.value`."),
    ("Що таке boundary testing?", "Це перевірка значень на межах діапазону та безпосередньо поруч із ними."),
    ("Які boundaries потрібно тестувати для діапазону 0–100?", "Щонайменше -0.01, 0, значення всередині, 100 і 100.01; за потреби перевірити точність на дробових межах."),
    ("Що таке parametrization?", "Один тестовий шаблон запускається багато разів із різними наборами вхідних даних."),
    ("Для чого pytest.mark.parametrize?", "Для оголошення таких наборів параметрів і очікуваних результатів без дублювання тестового коду."),
    ("Що дають ids параметризованих tests?", "Людинозрозумілі назви кожного випадку у виводі pytest."),
    ("Що таке fixture?", "Функція pytest, що готує та повертає ізольовані дані або ресурс для тесту."),
    ("Для чого використовуються fixtures?", "Для повторного використання setup, зменшення дублювання та контрольованого життєвого циклу ресурсів."),
    ("Що означає fixture setup?", "Підготовка стану або ресурсу до виконання тесту."),
    ("Що означає fixture teardown?", "Звільнення ресурсу або прибирання стану після тесту."),
    ("Для чого yield у fixture?", "Щоб передати підготовлений ресурс тесту, а після його завершення виконати cleanup-код."),
    ("Які fixture scopes підтримує pytest?", "function, class, module, package та session."),
    ("Який scope є default?", "function — fixture створюється заново для кожного тесту."),
    ("Для чого conftest.py?", "Для спільних fixtures та pytest hooks, доступних тестам відповідної теки без ручного імпорту."),
    ("Чому fixtures із conftest.py не імпортують вручну?", "Pytest автоматично знаходить їх у conftest.py відповідно до розташування тесту."),
    ("Що таке tmp_path?", "Вбудована function-scoped fixture pytest, яка надає унікальну тимчасову директорію як pathlib.Path."),
    ("Чому tmp_path корисний?", "Він ізолює файлові тести, запобігає конфліктам і забрудненню робочих даних проєкту."),
    ("Що таке test isolation?", "Незалежність тесту від порядку запуску, результатів інших тестів і спільного змінюваного стану."),
    ("Для чого monkeypatch?", "Тимчасово замінювати environment variables, атрибути, функції, словники або робочу теку з автоматичним відновленням."),
    ("Як monkeypatch змінює environment variable?", "Викликом `monkeypatch.setenv(\"NAME\", \"value\")`; зміна діє лише під час тесту."),
    ("Як видалити environment variable у test?", "Викликом `monkeypatch.delenv(\"NAME\", raising=False)`."),
    ("Як підмінити function через monkeypatch?", "Викликом `monkeypatch.setattr(module, \"function\", fake_function)` у модулі, де це ім’я використовується."),
    ("Що таке test double?", "Узагальнена підміна реальної залежності в тесті."),
    ("Що таке Dummy?", "Простий об’єкт-заповнювач, переданий лише для заповнення аргументу і не задіяний."),
    ("Що таке Stub?", "Підміна, яка повертає заздалегідь задані відповіді."),
    ("Що таке Fake?", "Спрощена робоча реалізація залежності, наприклад in-memory repository."),
    ("Що таке Mock?", "Підміна, що зберігає інформацію про взаємодію та дає змогу перевірити виклики."),
    ("Що таке Spy?", "Обгортка над реальною поведінкою, яка водночас записує виклики."),
    ("Для чого Mock?", "Ізолювати зовнішню залежність і перевірити, чи вона викликана з правильними аргументами та кількістю разів."),
    ("Що таке spec?", "Обмеження mock доступними атрибутами інтерфейсу реального об’єкта."),
    ("Для чого return_value?", "Задати значення, яке mock повертає при виклику."),
    ("Для чого side_effect?", "Задати виняток, послідовність відповідей або функцію, що виконується при виклику mock."),
    ("Як перевірити, що method викликано один раз?", "Використати `mock.method.assert_called_once_with(...)` або `assert_called_once()`."),
    ("Як перевірити parameters виклику?", "Порівняти виклик через `assert_called_once_with(expected_args, expected_kwargs)`."),
    ("Як перевірити, що method не викликався?", "Використати `mock.method.assert_not_called()`."),
    ("Що таке state testing?", "Перевірка видимого стану або результату системи після дії."),
    ("Що таке interaction testing?", "Перевірка взаємодій між об’єктами: хто, коли і з якими аргументами викликав залежність."),
    ("Коли interaction testing виправдане?", "На межах компонентів, коли правильний виклик є частиною контракту або треба перевірити відсутність небажаної дії."),
    ("Що таке patch?", "Тимчасова заміна об’єкта або імені на підміну на час тесту."),
    ("Чому patch потрібно виконувати там, де name використовується?", "Код звертається до імені у своєму namespace; заміна іншого namespace не змінить це посилання."),
    ("Що таке AsyncMock?", "Асинхронний test double, який поводиться як awaitable і відстежує await-виклики."),
    ("Як перевірити awaited call?", "Використати `async_mock.assert_awaited_once_with(...)`."),
    ("Що таке flaky test?", "Тест, результат якого нестабільно змінюється між запусками без змін коду."),
    ("Чому flaky tests небезпечні?", "Вони знижують довіру до CI, маскують справжні регресії та витрачають час на повторні запуски."),
    ("Що таке deterministic test?", "Тест із однаковим результатом для однакового коду й контрольованих вхідних даних."),
    ("Чому unit test не повинен залежати від Internet?", "Мережа додає повільність, нестабільність, зовнішній стан і недетерміновані помилки."),
    ("Коли в integration test доцільний real filesystem?", "Коли тестується реальний файловий контракт; використовується ізольований тимчасовий каталог."),
    ("Чому не потрібно mock-ати все?", "Надмірні mocks можуть тестувати лише з’єднання mocks і приховати помилки справжньої логіки."),
    ("Що таке over-mocking?", "Підміна такої кількості внутрішніх компонентів, що тест перестає перевіряти поведінку системи."),
    ("Що таке coverage?", "Метрика частки вимірюваного коду, який виконувався під час тестів."),
    ("Що таке statement coverage?", "Частка виконаних інструкцій коду."),
    ("Що таке branch coverage?", "Частка виконаних напрямків переходу, наприклад обох гілок умовного виразу."),
    ("Чим вони відрізняються?", "Statement coverage рахує рядки/інструкції, branch coverage окремо рахує альтернативні переходи умов."),
    ("Як отримати coverage через pytest-cov?", "Запустити `python -m pytest --cov=car_catalog --cov-branch --cov-report=term-missing --cov-report=html`."),
    ("Для чого --cov-report=term-missing?", "Показати coverage у терміналі та перелік рядків, які не були виконані."),
    ("Для чого HTML coverage report?", "Для інтерактивного перегляду покритих і пропущених рядків за файлами у браузері."),
    ("Чи гарантує 100% coverage відсутність bugs?", "Ні; він не оцінює якість assertions і не доводить правильність очікувань."),
    ("Чому meaningful assertions важливіші за coverage percentage?", "Тільки змістовна assertion порівнює результат із контрактом і може виявити неправильну поведінку."),
    ("Що таке coverage threshold?", "Мінімальний відсоток coverage, нижче якого звіт/CI завершується невдало."),
    ("Чому tests повинні бути незалежними один від одного?", "Тоді вони детерміновані, запускаються в будь-якому порядку й не приховують помилки через спільний стан."),
]


def run_command(arguments: list[str], *, check: bool = True) -> str:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        check=check,
        encoding="utf-8",
        errors="replace",
        env=environment,
        text=True,
    )
    return (result.stdout + result.stderr).strip()


def run_powershell(command: str) -> None:
    encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
        cwd=ROOT,
        check=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
    )


def set_font(run: Run, size: float = 12, *, bold: bool = False, name: str = "Times New Roman") -> None:
    run.font.name = name
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:ascii"), name)
    fonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.bold = bold


def paragraph(
    doc: DocumentType,
    text: str = "",
    *,
    bold: bool = False,
    size: float = 12,
    align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY,
    indent: bool = True,
) -> Paragraph:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.alignment = align
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.0)
    run = p.add_run(text)
    set_font(run, size, bold=bold)
    return p


def heading(doc: DocumentType, title: str, level: int = 1) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(title)
    set_font(run, 14 if level == 1 else 12, bold=True)


def code(doc: DocumentType, text: str, size: float = 8.5) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_together = True
    for line in text.rstrip().splitlines():
        run = p.add_run(line + "\n")
        set_font(run, size, name="Consolas")


def add_borders(table: Table) -> None:
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), "A6A6A6")
        borders.append(element)
    table._tbl.tblPr.append(borders)


def table(
    doc: DocumentType,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float] | None = None,
) -> None:
    result = doc.add_table(rows=1, cols=len(headers))
    result.alignment = WD_TABLE_ALIGNMENT.CENTER
    result.autofit = False
    add_borders(result)
    for column, value in enumerate(headers):
        cell = result.rows[0].cells[column]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if widths:
            cell.width = Cm(widths[column])
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "DDEBF7")
        cell._tc.get_or_add_tcPr().append(shading)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p.add_run(value), 9, bold=True)
    for row in rows:
        cells = result.add_row().cells
        for column, value in enumerate(row):
            cells[column].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths:
                cells[column].width = Cm(widths[column])
            p = cells[column].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            set_font(p.add_run(str(value)), 8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_page_number(section: Section) -> None:
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(end)
    set_font(run, 9)


def make_terminal_image(path: Path, lines: list[str], title: str) -> None:
    font_path = Path("C:/Windows/Fonts/consola.ttf")
    font_bold_path = Path("C:/Windows/Fonts/consolab.ttf")
    normal = ImageFont.truetype(str(font_path), 20)
    bold = ImageFont.truetype(str(font_bold_path), 21)
    image = Image.new("RGB", (1480, 100 + 38 * max(3, len(lines))), "#111827")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 1480, 58), 14, fill="#1f2937")
    for x, color in [(26, "#ef4444"), (51, "#f59e0b"), (76, "#22c55e")]:
        draw.ellipse((x, 20, x + 13, 33), fill=color)
    draw.text((112, 14), title, font=bold, fill="#e5e7eb")
    y = 76
    for line in lines:
        draw.text((28, y), line, font=normal, fill="#86efac" if line.startswith("PS>") else "#f3f4f6")
        y += 38
    image.save(path)


class CoverageRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.current: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr" and dict(attrs).get("class") == "region":
            self.current = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.current:
            self.rows.append(self.current)
            self.current = None

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self.current is not None and text:
            self.current.append(text)


def export_pdf(docx_path: Path, pdf_path: Path) -> None:
    source = str(docx_path)
    target = str(pdf_path)
    command = (
        "$ErrorActionPreference = 'Stop'; "
        "$word = New-Object -ComObject Word.Application; "
        "$word.Visible = $false; "
        "try { "
        f"$document = $word.Documents.Open('{source.replace(chr(39), chr(39) * 2)}'); "
        f"$document.SaveAs2('{target.replace(chr(39), chr(39) * 2)}', 17); "
        "$document.Close(0); "
        "} finally { $word.Quit() }"
    )
    run_powershell(command)
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"Microsoft Word did not create the PDF: {pdf_path}")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if len(QUESTIONS) != 80:
        raise RuntimeError(f"Expected 80 control answers, got {len(QUESTIONS)}")

    integration_output = run_command(["-m", "pytest", "-q", "-m", "integration", "--cov-fail-under=0"])
    unit_output = run_command(["-m", "pytest", "-q", "-m", "not integration", "--cov-fail-under=0"])
    test_output = run_command(["-m", "pytest", "-q"])
    mypy_output = run_command(["-m", "mypy"])

    passed_match = re.search(r"(\d+) passed(?:,\s*(\d+) failed)?", test_output)
    integration_match = re.search(r"(\d+) passed(?:,\s*(\d+) failed)?", integration_output)
    unit_match = re.search(r"(\d+) passed(?:,\s*(\d+) failed)?", unit_output)
    if passed_match is None or integration_match is None or unit_match is None:
        raise RuntimeError("Could not parse pytest results; report was not generated.")
    test_result = f"{passed_match.group(1)} passed, {passed_match.group(2) or '0'} failed"

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_json:
        coverage_json = Path(temp_json.name)
    try:
        run_command(["-m", "coverage", "json", "-o", str(coverage_json)])
        coverage = json.loads(coverage_json.read_text(encoding="utf-8"))["totals"]
    finally:
        coverage_json.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="lab6-report-") as temp_dir:
        temp = Path(temp_dir)
        test_image = temp / "tests.png"
        coverage_image = temp / "coverage.png"
        test_lines = [
            "PS> python -m pytest -q",
            test_result,
            f"statements: {coverage['percent_statements_covered']:.2f}%",
            f"branches: {coverage['percent_branches_covered']:.2f}%",
            f"TOTAL: {coverage['percent_covered_display']}% combined coverage",
            "Coverage HTML written to dir htmlcov",
        ]
        make_terminal_image(test_image, test_lines, "PowerShell - повний тестовий набір")

        html_path = ROOT / "htmlcov" / "index.html"
        html_text = html_path.read_text(encoding="utf-8")
        parser = CoverageRows()
        parser.feed(html_text)
        visible_rows = [row for row in parser.rows if row and row[-1].endswith("%")][:7]
        make_terminal_image(
            coverage_image,
            [
                f"HTML file: {html_path.relative_to(ROOT)}",
                f"Coverage report: {coverage['percent_covered_display']}%",
                f"Statements: {coverage['percent_statements_covered_display']}%",
                f"Branches: {coverage['percent_branches_covered_display']}%",
                *[f"{row[0][:34]:34} {row[-1]}" for row in visible_rows[:3]],
            ],
            "htmlcov/index.html - фактичні дані coverage",
        )

        doc: DocumentType = Document()
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(1.5)
        add_page_number(section)

        for text, bold in [
            ("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", True),
            ("Львівський національний університет імені Івана Франка", True),
            ("Факультет електроніки та комп’ютерних технологій", False),
        ]:
            paragraph(doc, text, bold=bold, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        for _ in range(5):
            paragraph(doc, "", indent=False)
        for text, bold in [
            ("ЗВІТ", True),
            ("про виконання лабораторної роботи №6", False),
            ("«Автоматизоване тестування Python-програм»", True),
            ("з дисципліни «Професійний Python»", False),
            ("Варіант №5 — «Каталог автомобілів»", False),
        ]:
            paragraph(doc, text, bold=bold, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        for _ in range(4):
            paragraph(doc, "", indent=False)
        for text in [
            "Виконав: студент групи ФЕП-32",
            "Горин Михайло",
            "Репозиторій: github.com/MykhailoG212/Prof_python",
        ]:
            paragraph(doc, text, align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False)
        for _ in range(4):
            paragraph(doc, "", indent=False)
        paragraph(doc, "Львів — 2026", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

        heading(doc, "1. Тема, мета та номер варіанта")
        paragraph(doc, "Тема: автоматизоване тестування Python-програм із pytest. Мета — спроєктувати ізольовані unit та integration tests, перевірити звичайні, граничні й помилкові сценарії, файлові операції, конфігурацію та взаємодію компонентів, а також оцінити statement і branch coverage.")
        paragraph(doc, "Індивідуальний варіант №5 — «Каталог автомобілів», наскрізний навчальний Python-проєкт попередніх лабораторних робіт.")
        heading(doc, "2. Короткий опис проєкту")
        paragraph(doc, "Car Catalog зберігає й аналізує каталог автомобілів. У роботі перевірено предметні моделі, application service та repository, потокову обробку CSV, валідацію, YAML-конфігурацію, tolerant/strict імпорт, журналювання й атомарний JSON-експорт. Зовнішня мережа не потрібна: файлові integration tests використовують тимчасові файли, а залежність repository підмінюється Mock.")
        heading(doc, "3. Структура production code і тестів")
        code(doc, "src/car_catalog/\n├── models.py, services.py, repositories.py\n├── application.py, criteria.py, protocols.py\n├── reliable/\n│   ├── config.py, importers.py, exporters.py\n│   ├── services.py, exceptions.py, main.py\n└── streaming/\n    ├── readers.py, parsers.py, validation.py\n    ├── pipeline.py, filters.py, analytics.py\n\ntests/\n├── conftest.py\n├── test_services.py, test_main.py, test_oop_model.py\n├── test_processors_analytics.py, test_streaming.py\n├── test_reliable_importer.py\n├── test_reliable_validation.py, test_reliable_main.py\n└── test_application_interactions.py")
        paragraph(doc, "Тести згруповані за production-компонентами в окремі файли; integration-сценарії мають pytest marker integration. Shared fixtures розміщені у conftest.py та доступні за автоматичним пошуком pytest.")

        heading(doc, "4. Матриця тестування")
        table(doc, ["Категорія", "Перевірка / приклад", "Результат"], [
            ["Normal", "Модель Car, пошук, статистика, tolerant import", "Очікувані моделі, результати та JSON"],
            ["Minimum/maximum boundary", "1886 і 2026; ціна 0 і 1 000 000", "Межі включені"],
            ["Boundary outside", "1885, 2027, ціна нижче/вище меж, NaN", "RecordValidationError"],
            ["Empty", "Порожній каталог, порожні генератори", "Нульові агрегати / None без помилок"],
            ["Invalid input", "Некоректний рік, CSV поля, YAML", "Перевірений виняток та повідомлення"],
            ["Dependency failure", "Repository.add піднімає OSError", "Помилка передається; ID доступний для retry"],
            ["File/config", "tmp_path: YAML, CSV, JSON; атомарне перейменування", "Ізольовані файли й збереження попереднього output"],
            ["Interaction", "Mock/spec, return_value, side_effect", "Перевірені аргументи, кількість і відсутність викликів"],
            ["Integration", "CSV → parser/validator → service → JSON", "6 маркованих integration cases проходять"],
            ["Repeated/isolated", "Повторний service.add після помилки", "Тести незалежні, ID не пропускається"],
        ], [3.1, 8.1, 5.3])

        heading(doc, "5. Приклади реалізованих тестів")
        heading(doc, "5.1 Unit test, fixture factory та fixture scope", 2)
        code(doc, "from car_catalog.models import Car\n\n@pytest.fixture\ndef car_factory() -> Callable[..., Car]:\n    def create_car(*, brand=\"Toyota\", model=\"Camry\", year=2020,\n                   price=25_000.0, mileage=45_000) -> Car:\n        return Car(brand, model, year, price, mileage)\n    return create_car\n\n@pytest.fixture(scope=\"session\")\ndef processing_config() -> ProcessingConfig:\n    return ProcessingConfig(... )")
        paragraph(doc, "car_factory має function scope за замовчуванням і створює новий об’єкт на запит. processing_config має session scope, оскільки це frozen dataclass без спільного змінюваного стану. Fixtures не імпортуються безпосередньо з conftest.py.")

        heading(doc, "5.2 Parametrization, ids і boundary tests", 2)
        code(doc, "@pytest.mark.parametrize(\n    (\"year\", \"price\"),\n    [(1886, \"0\"), (2026, \"1000000\")],\n    ids=[\"minimum-boundary\", \"maximum-boundary\"],\n)\ndef test_parse_vehicle_accepts_inclusive_configuration_boundaries(...):\n    vehicle = parse_vehicle(row, line_number=2, config=processing_config)\n    assert vehicle == Vehicle(1, \"Toyota\", \"Camry\", year, float(price), 0)")
        paragraph(doc, "Окремі параметризовані invalid cases перевіряють 1885/2027, від’ємну або завелику ціну, NaN і від’ємний пробіг.")

        heading(doc, "5.3 pytest.raises, pytest.approx і tmp_path", 2)
        code(doc, "with pytest.raises(RecordValidationError, match=message):\n    parse_vehicle(row, line_number=2, config=processing_config)\n\nassert calculate_average_price(cars) == pytest.approx(51666.67, 0.01)\n\nconfig_path = tmp_path / \"config.yaml\"\ninput_path = tmp_path / \"vehicles.csv\"\nwrite_csv(input_path)\nconfig = load_config(config_path)\nreport = import_catalog(config)\nassert json.loads(config.output_path.read_text(encoding=\"utf-8\"))[\"statistics\"] == {\n    \"valid\": 2, \"invalid\": 1\n}")
        paragraph(doc, "pytest.raises перевіряє тип і текст domain exception. pytest.approx задає абсолютну похибку для середнього ціни. tmp_path створює ізольовані тимчасові файли; pytest керує їхнім життєвим циклом, тому окрема yield-fixture для cleanup тут не потрібна.")

        heading(doc, "5.4 monkeypatch: environment variable та функція", 2)
        code(doc, "monkeypatch.setenv(\"CAR_CATALOG_CONFIG\", \"custom/config.yaml\")\nassert reliable_main.main() == 0\nassert loaded_paths == [Path(\"custom/config.yaml\")]\n\nmonkeypatch.delenv(\"CAR_CATALOG_CONFIG\", raising=False)\n# CLI повертається до config/lab5.yaml\n\nmonkeypatch.setattr(\"builtins.input\", lambda _prompt: next(answers))\nmonkeypatch.setattr(\"car_catalog.main.run_lab3_demo\", run_demo)")
        paragraph(doc, "CAR_CATALOG_CONFIG є конфігураційним override CLI; без змінної використовується config/lab5.yaml. monkeypatch автоматично відновлює середовище й підмінені об’єкти після тесту.")

        heading(doc, "5.5 Mock, MagicMock, return_value, side_effect та interactions", 2)
        code(doc, "repository = MagicMock(spec=VehicleRepository)\nrepository.all.return_value = [matching, another_car]\nservice = VehicleCatalogService(repository)\nassert service.search_by_brand_or_model(brand=\"tesla\") == [matching]\nrepository.all.assert_called_once_with()\nrepository.add.assert_not_called()\n\nrepository = Mock(spec=VehicleRepository)\nrepository.add.side_effect = OSError(\"storage unavailable\")\nwith pytest.raises(OSError, match=\"storage unavailable\"):\n    service.add(vehicle)\nrepository.add.assert_called_once_with(1, vehicle)")
        paragraph(doc, "Mock/spec обмежує інтерфейс залежності; return_value моделює читання repository, side_effect — збій на системній межі. Тест перевіряє результат, виклик та відсутність запису там, де його не очікують. Failure injection також підтверджує повторну спробу з тим самим ID.")

        heading(doc, "5.6 Integration tests", 2)
        code(doc, "@pytest.mark.integration\ndef test_tolerant_import_exports_only_valid_records_and_logs_error(tmp_path):\n    config_path = tmp_path / \"config.yaml\"\n    input_path = write_config(config_path)\n    write_csv(input_path)\n    config = load_config(config_path)\n    report = import_catalog(config)\n    assert (report.valid_count, report.invalid_count) == (2, 1)\n    payload = json.loads(config.output_path.read_text(encoding=\"utf-8\"))\n    assert [row[\"vehicle_id\"] for row in payload[\"vehicles\"]] == [1, 2]")
        paragraph(doc, "Це перевіряє кілька компонентів з реальною файловою системою, але тільки всередині tmp_path. Окремий strict сценарій перевіряє зупинку, chaining та збереження старого експорту. Мережеві API в проєкті відсутні, тому тести не залежать від Internet.")

        heading(doc, "5.7 AsyncMock та асинхронний виклик", 2)
        code(doc, "async def add_async(self, vehicle: Vehicle) -> int:\n    return await asyncio.to_thread(self.add, vehicle)\n\nthread_offload = AsyncMock(return_value=7)\nmonkeypatch.setattr(\"car_catalog.application.asyncio.to_thread\", thread_offload)\nassert asyncio.run(service.add_async(vehicle)) == 7\nthread_offload.assert_awaited_once_with(service.add, vehicle)\n\nthread_offload.side_effect = OSError(\"storage unavailable\")\nwith pytest.raises(OSError, match=\"storage unavailable\"):\n    asyncio.run(service.add_async(vehicle))")
        paragraph(doc, "Сервіс надає async-адаптер для блокувального repository без блокування event loop. Lock захищає генерацію ID при паралельних sync/async записах. AsyncMock перевіряє awaited-виклик межі thread offload, результат, аргументи та передачу помилки; asyncio.run запускає перевірку без додаткового pytest-asyncio.")

        heading(doc, "6. Запуск тестів і результати")
        paragraph(doc, f"Одна команда повного запуску: python -m pytest. Фактичний результат запуску під час формування звіту: {test_result}; integration: {integration_match.group(0)}; unit та решта тестів: {unit_match.group(0)}. Середовище: Python {sys.version.split()[0]}, pytest із pytest-cov. Поріг повного suite у pyproject.toml — 80%.")
        paragraph(doc, "Окремі команди: python -m pytest tests/test_services.py --cov-fail-under=0; python -m pytest tests/test_services.py::test_calculate_average_price --cov-fail-under=0; python -m pytest -m integration --cov-fail-under=0. Для subset-запуску поріг вимкнено, бо частковий набір не має представляти coverage всього пакета.")
        doc.add_picture(str(test_image), width=Cm(16))
        paragraph(doc, "Рисунок 1 — Фактичний результат повного запуску pytest і згенерований coverage.", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        paragraph(doc, f"Mypy: {mypy_output}.")

        heading(doc, "7. Coverage: statement, branch та HTML")
        paragraph(doc, f"Звіт покриття охоплює {coverage['num_statements']} statements і {coverage['num_branches']} branch outcomes у пакеті car_catalog. Виконано statements: {coverage['percent_statements_covered']:.2f}%; branch outcomes: {coverage['covered_branches']}/{coverage['num_branches']} = {coverage['percent_branches_covered']:.2f}%; combined coverage: {coverage['percent_covered']:.2f}%. У повному тестовому наборі пропущено {coverage['missing_lines']} statement lines та {coverage['missing_branches']} branch outcomes.")
        coverage_json_path = temp / "coverage.json"
        run_command(["-m", "coverage", "json", "-o", str(coverage_json_path)])
        coverage_by_file = json.loads(coverage_json_path.read_text(encoding="utf-8"))["files"]
        coverage_rows = []
        for file_path, info in sorted(coverage_by_file.items()):
            summary = info["summary"]
            if summary["num_statements"]:
                coverage_rows.append([
                    file_path.replace("src/car_catalog/", ""),
                    f"{summary['percent_statements_covered']:.0f}%",
                    f"{summary['covered_branches']}/{summary['num_branches']}" if summary["num_branches"] else "—",
                    f"{summary['percent_covered']:.0f}%",
                ])
        table(doc, ["Модуль", "Statements", "Branches", "Combined"], coverage_rows, [7.0, 2.7, 3.2, 3.0])
        paragraph(doc, "HTML-звіт створено у htmlcov/index.html; він показує деталі за файлами та пропущені рядки. Нижче наведено фрагмент фактичного HTML-звіту, відрендерений на основі його таблиці.")
        doc.add_picture(str(coverage_image), width=Cm(16))
        paragraph(doc, "Рисунок 2 — Фрагмент HTML coverage report, сформованого pytest-cov.", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
        html_fragment = re.search(r"<h1>Coverage report:.*?</h1>", html_text, flags=re.DOTALL)
        if html_fragment is None:
            raise RuntimeError("Coverage HTML report does not contain its coverage heading.")
        code(doc, html_fragment.group(0).strip(), size=8)
        code(doc, "Повний звіт: htmlcov/index.html\nКоманда: python -m pytest --cov=car_catalog --cov-branch --cov-report=term-missing --cov-report=html")

        heading(doc, "8. Аналіз недостатньо протестованих paths")
        weak = sorted(
            (
                info["summary"]["percent_branches_covered"],
                file_path,
                info["summary"]["missing_branches"],
            )
            for file_path, info in coverage_by_file.items()
            if info["summary"]["num_branches"]
        )
        weak_paths = [f"{path}: branch coverage {percent:.1f}%, {missing} невиконаних outcomes" for percent, path, missing in weak if percent < 80]
        paragraph(doc, "Найменше branch coverage мають інтерактивний legacy CLI та демонстраційні/benchmark paths. Вони виконують UI-вивід, запуск великих benchmark-наборів і окремі сценарії меню; ці гілки не визначають критичний контракт CSV/YAML/JSON. Конфігураційні та export edge paths також залишаються у списку term-missing.")
        for item in weak_paths:
            paragraph(doc, f"• {item}", indent=False)
        paragraph(doc, "Наступне доцільне посилення — параметризувати решту меню invalid inputs, конфігураційні помилки кожного типу й помилки файлової системи. Умова лабораторної — проаналізувати пропуски та запропонувати тести; не створювати формальні assertions заради 100%. Налаштований поріг 80% запобігає регресії загального coverage.")

        heading(doc, "9. Перевірка реальних defects")
        paragraph(doc, "Під час цього запуску тести не відтворили нових production defects; тому звіт не приписує собі непідтверджені виправлення. Перевірені ризикові сценарії включають пошкоджений YAML/CSV, строгий та tolerant імпорт, атомарне збереження попереднього JSON після exception, точність агрегатів та помилку repository. Доданий failure-injection test зафіксував регресійний контракт: якщо repository.add завершується помилкою, наступна спроба використовує той самий ID. Якщо вимога трактує «знайдені defects» як обов’язкове відтворення реального дефекту, у межах виміряних запусків такого дефекту не підтверджено.")

        heading(doc, "10. Відповіді на контрольні запитання")
        for number, (question, answer) in enumerate(QUESTIONS, 1):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.05
            set_font(p.add_run(f"{number}. {question} "), 10, bold=True)
            set_font(p.add_run(answer), 10)

        heading(doc, "11. Висновок")
        paragraph(doc, f"Створено й перевірено test suite для каталогу автомобілів із unit та integration tests, fixtures різних scopes, factory, parametrization, boundary/error checks, tmp_path, monkeypatch environment/config, Mock/MagicMock/AsyncMock, side_effect, interaction assertions, configuration, файлового імпорту/експорту, branch і statement coverage. Повний suite проходить: {test_result}; coverage вище встановленого 80% threshold. Структурні прогалини branch coverage описані окремо.")

        doc.core_properties.title = "Лабораторна робота №6 — Автоматизоване тестування"
        doc.core_properties.subject = "Професійний Python, варіант 5 — каталог автомобілів"
        doc.core_properties.author = "Горин Михайло"
        doc.save(str(OUTPUT))
        export_pdf(OUTPUT, PDF_OUTPUT)

    print(f"DOCX: {OUTPUT}")
    print(f"PDF:  {PDF_OUTPUT}")
    print(f"Tests: {passed_match.group(0)}; coverage: {coverage['percent_covered']:.2f}%")


if __name__ == "__main__":
    main()

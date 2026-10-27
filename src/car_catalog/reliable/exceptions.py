"""Предметно-орієнтована ієрархія помилок ЛР5."""


class ApplicationError(Exception):
    """Базова помилка застосунку."""


class ConfigurationError(ApplicationError):
    """Конфігурація відсутня або містить недопустимі значення."""


class DataError(ApplicationError):
    """Базова помилка зовнішніх даних."""


class DataImportError(DataError):
    """Вхідний файл неможливо прочитати або розібрати."""


class RecordValidationError(DataError):
    """Один CSV-запис не відповідає схемі каталогу."""

    def __init__(self, message: str, *, line_number: int, field: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field


class DataExportError(DataError):
    """Вихідний JSON не вдалося безпечно записати."""

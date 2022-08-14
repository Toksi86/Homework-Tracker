class SatusCodeNot200(Exception):
    """Исключение при недоустпности API-сервиса."""


class DictIsEmpty(Exception):
    """Исключение при пустом словаре."""


class ResponseNotDict(Exception):
    """Ответ не является словарем."""


class HomeworksNotList(Exception):
    """Ответ не является словарем."""

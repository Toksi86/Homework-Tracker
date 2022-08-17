class SatusCodeNot200Error(Exception):
    """Exception: API-сервис недоступен."""


class SendMsgError(Exception):
    """Exception: Ошибка отправки сообщения."""


class TokenError(Exception):
    """Exception: Токены пустые или некорректные."""


class ResponseError(Exception):
    """Exception: Ошибка при отправе запроса."""

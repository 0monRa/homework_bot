class TokenDosentExistError(Exception):
    pass


class TokenIsEmptyError(Exception):
    pass


class TelegramAPIError(Exception):
    pass


class TelegramAPIStatusCodeError(Exception):
    pass


class HomeworkStatusError(Exception):
    """Исключение для ошибок статуса домашней работы."""
    pass

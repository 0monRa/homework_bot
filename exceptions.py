class TokenDosentExistError(Exception):
    pass


class TokenIsEmptyError(Exception):
    pass


class TelegramAPIError(Exception):
    pass


class TelegramAPIStatusCodeError(Exception):
    pass


class TelegramSendMessageError(Exception):
    pass


class JSONCodeError(Exception):
    pass

import exceptions
import logging
import os
import requests
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telebot import TeleBot

load_dotenv()

TIME_FOR_CHECK_HOMEWORKS = 120

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    token_list = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    token_missed = []
    token_empty = []

    for name, token in token_list.items():
        if token is None:
            token_missed.append(name)
        if token == '':
            token_empty.append(name)

    if token_missed or token_empty:
        tokens_error = ', '.join(token_missed)
        logging.critical(f'Missing environment variables: {tokens_error}')
        if token_missed:
            tokens_error = ", ".join(token_missed)
            raise exceptions.TokenDosentExistError(
                f'Не существует следующих переменных: {tokens_error}'
            )
        if token_empty:
            tokens_error = ", ".join(token_empty)
            raise exceptions.TokenIsEmptyError(
                f'Следующие переменные не могут быть путсыми: {tokens_error}'
            )
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except Exception as error:
        raise exceptions.TelegramSendMessageError(
            f'Ошибка при отправке сообщения: {error}'
        )


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
    except requests.RequestException as error:
        raise exceptions.TelegramAPIError(
            f'Ошибка при запросе к API: {error}'
        )

    if response.status_code != HTTPStatus.OK:
        raise exceptions.TelegramAPIStatusCodeError(
            f'API вернул статус {response.status_code}'
        )

    try:
        response_json = response.json()
    except ValueError as error:
        raise exceptions.JSONCodeError(f'Ошибка при запросе JSON: {error}')

    return response_json


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем.')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ "homeworks".')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Значение по ключу "homeworks" не является списком.')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус работы из информации о конкретной домашней работе."""
    if 'status' not in homework or 'homework_name' not in homework:
        raise KeyError('В домашней работе отсутствуют необходимые ключи.')
    status = homework['status']
    homework_name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы программы."""
    if not check_tokens():
        return

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time()) - TIME_FOR_CHECK_HOMEWORKS
    last_error = str()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug('Статус не изменился.')
            timestamp = response.get("current_date", timestamp)
            last_error = ''
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if last_error != message:
                try:
                    send_message(bot, message)
                    last_error = message
                except exceptions.TelegramSendMessageError as send_error:
                    logging.error(
                        f'Ошибка при отправке сообщения: {send_error}'
                    )
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

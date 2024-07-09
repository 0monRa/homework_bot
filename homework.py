import exceptions
import logging
import os
import requests
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telebot import TeleBot

load_dotenv()

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

    for name, token in token_list.items():
        if token is None:
            raise exceptions.TokenDosentExistError(
                f'Переменной {name} не существует!'
            )
        if token == '':
            raise exceptions.TokenIsEmptyError(
                f'Значение переменной {name} не может быть пустым!'
            )
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except Exception as error:
        logging.error(f'Произошел сбой при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            logging.error(f'Status code: {response.status_code}.')
            raise exceptions.TelegramAPIStatusCodeError(
                f'API вернул статус {response.status_code}'
            )
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise exceptions.TelegramAPIError(
            f'Ошибка при запросе к API: {error}'
        )


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
    try:
        check_tokens()
    except (
        exceptions.TokenDosentExistError,
        exceptions.TokenIsEmptyError
    ) as error:
        logging.critical(error)
        return

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug('Статус не изменился.')
            timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

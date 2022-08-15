import os
import requests
import time
from dotenv import load_dotenv
from http import HTTPStatus

import logging
from logging import FileHandler
import telegram

import exceptions as exc

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = FileHandler('my_logger.log', encoding='UTF-8')
logger.addHandler(file_handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s '
    '- %(funcName)s - %(lineno)d'
)
file_handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

#  Исправил на VERDICTS. Пременная была создана не мной.
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение пользователю о новом статусе."""
    try:
        logger.debug('Попытка отправить сообщение')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено')
    except telegram.error.TelegramError as error:
        raise exc.SendMsgError(error)


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        error = f'API-сервис недоступен, код ответа {response.status_code}'
        raise exc.SatusCodeNot200Error(error)


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            'Аргумент функции check_response не является словарем. '
            f'Полученный тип данных: {type(response)}'
        )
    if 'homeworks' not in response:
        raise KeyError('Ключ homewowks отсуствует в response')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Домашняя работа представленая в response по ключу homeworks '
            'реализована не в виде словаря. '
            f'Полученный тип данных: {type(response["homeworks"])}'
        )
    return response['homeworks']


def parse_status(homework):
    """Получение статуса домашней работы."""
    if 'homework_name' not in homework or (
       'status' not in homework
    ):
        raise KeyError(
            'В словаре homework отсутствуют требуемые ключи: '
            '"homework_name", "status"'
        )
    homework_name = homework['homework_name']
    homework_verdict = homework['status']
    if homework_verdict in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_verdict]
        message = (
            f'Изменился статус проверки работы "{homework_name}". '
            f'{verdict}'
        )
        return message
    else:
        raise KeyError(
            f'Недокументированный статус домашней работы: '
            f'{homework_verdict}'
        )


def check_tokens():
    """Проверка наличия обязательных токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют необходимые токены.')
        raise exc.TokenError(
            'Отсутствуют необходимые токены: '
            '"PRACTICUM_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                status = parse_status(homework[0])
                send_message(bot, status)
            if 'current_date' in response:
                #  Можно пояснения — не совсем понятная для меня логика.
                #  По первому аргументу 'current_date' мы получаем дату ответа,
                #  а второй аргумент у метода гет что делает?
                current_timestamp = response.get(
                    'current_date',
                    current_timestamp
                )
        except Exception as error:
            logger.exception(
                f'Бот не смог отправить'
                f'сообщение из-за ошибки: {error}'
            )
            message = f'Сбой в работе программы: {error}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

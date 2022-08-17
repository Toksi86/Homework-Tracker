import os
import requests
import sys
import time
from dotenv import load_dotenv
from http import HTTPStatus

import logging
from logging import FileHandler, StreamHandler
import telegram

import exceptions as exc

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = FileHandler('my_logger.log', encoding='UTF-8')
stream_handler = StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s '
    '- %(funcName)s - %(lineno)d'
)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

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
        raise exc.SendMsgError(
            f'Бот не смог отправить сообщение: "{message}". \n'
            f'Внутрення ошибка: {error}'
        )


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise exc.ResponseError(error)
    if response.status_code == HTTPStatus.OK:
        return response.json()
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
    if homework_verdict not in HOMEWORK_VERDICTS:
        raise KeyError(
            f'Недокументированный статус домашней работы: '
            f'{homework_verdict}'
        )
    verdict = HOMEWORK_VERDICTS[homework_verdict]
    message = (
        f'Изменился статус проверки работы "{homework_name}". '
        f'{verdict}'
    )
    return message


def check_tokens():
    """Проверка наличия обязательных токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют необходимые токены.')
        sys.exit(
            'Отсутствуют необходимые токены: '
            '"PRACTICUM_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_status = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                status = parse_status(homework[0])
                if old_status != status:
                    send_message(bot, status)
                    old_status = status
                else:
                    continue
            current_timestamp = response.get(
                'current_date',
                current_timestamp
            )
        except Exception as error:
            logger.exception(
                f'Ошибка: {error}'
            )
            message = f'Сбой в работе программы: {error}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)



if __name__ == '__main__':
    main()

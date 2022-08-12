import logging
import os

import requests
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 5
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение пользователю о новом статусе."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Невозможно отправить сообщение: {error}')


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Возникла ошибка: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error('Эндпоинт API-сервиса недоступен')
    else:
        logging.info('Эндпоинт API-сервиса доступен')
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if 'homeworks' in response:
        return response['homeworks']
    else:
        print('Релизовать исключение - неверный контекст')
        logging.error('Передан неверный контекст')


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework['lesson_name']
    homework_status = homework['status']

    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Недокументированный статус домашней работы')


def check_tokens():
    """Проверка наличия обязательных токенов."""
    if PRACTICUM_TOKEN is None:
        logging.critical('Отсутствует PRACTICUM_TOKEN')
        return False
    elif TELEGRAM_TOKEN is None:
        logging.critical('Отсутствует TELEGRAM_TOKEN')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('Отсутствует TELEGRAM_CHAT_ID')
        return False
    else:
        logging.info('Токены проверены')
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1
    while check_tokens():
        try:
            logging.info('Отправлен запрос к API сервису')
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                status = parse_status(homework[0])
                send_message(bot, status)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logging.error(f'Бот не смог отправить'
                          f'сообщение из-за ошибки: {error}')
            time.sleep(RETRY_TIME)
        else:
            logging.debug('Обновлений нет')


if __name__ == '__main__':
    main()

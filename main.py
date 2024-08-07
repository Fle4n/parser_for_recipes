from constants import *
from functions import *
from argparser import *
import logging

base_url = BASE_URL
main_url = MAIN_URL
path_db = PATH_DB

if __name__ == '__main__':
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    args = cmd_parser()

    if args.work:
        logger.info('Начало работы парсинга')
        recs = parsing(main_url, base_url, 0.5)
        logger.info('Парсинг завершен')
        write_db(path_db, recs)
        logger.info('Запись в базу данных завершена')

    if args.delete:
        clean_db(path_db)
        logger.info('Очистка базы данных завершена')

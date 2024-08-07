import argparse
from constants import MAIN_URL
from exceptions import ErrArgException


def cmd_parser():
    parser = argparse.ArgumentParser(
        description=f'Парсинг рецептов с сайта: {MAIN_URL}')
    parser.add_argument("-w", "--work", action='store_true', help="Запустить парсинг")
    parser.add_argument("-d", "--delete", help="Очистить таблицу в базе данных")

    args, unknown = parser.parse_known_args()
    if unknown:
        raise ErrArgException(f"Неизвестные аргументы: {unknown}")

    args = parser.parse_args()

    return args

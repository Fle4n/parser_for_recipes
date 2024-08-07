**Программа для парсинга сайта `https://www.russianfood.com/` в котегории "Запеканки".**

**`constants.py`** - файл, в котором содержатся все нужные ссылки и названия, которые мы будем использовать в программе, как константы.

```python
BASE_URL = "https://www.russianfood.com/"
MAIN_URL = "https://www.russianfood.com/recipes/bytype/?fid=539"
PATH_DB = "Recs.db"
```

`BASE_URL` - константа, в которой хранится ссылка на основной сайт, из неё мы будем составлять дальнейшие ссылки для посещения страничек с рецептами.

`MAIN_URL` - константа, в которой хранится ссылка на сайт, на котором находятся ссылки на все запеканки с сайта.

`PATH_DB` - Константа с названием для базы данных.

**`exceptions.py`** - файл, в котором содержится класс исключения для программы.

```python
class ErrArgException(Exception):
    def __init__(self, message="Некорректный аргумент парсинга"):
        self.message = message
        super().__init__(self.message)
```

`class ErrArgException` - класс исключения предназначенный для проверки - если введен дополнительный аргумент для парсинга, то вывести ошибку, если же ничего не введено, то дай программе дальше работать.

**`argparser.py`** - файл, который мы исользуем для запуска программы через командную строку. В нём у нас прописаны все нужная информация, которая может понадобиться для работы с файлом, котрую можно вызвать по комнде `python3 argparse.py -help` или `python3 argparse.py --h`(но если у вас ОС Windows, то команды нужно немного изменить - `python argparse.py -help` или `python argparse.py --h`)
```python
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
```
Модуль `argparse` мы импортируем для вызова программы из командной строки и удобному вызову определённых команд для скрипта.

В данном файле мы импортируем `MAIN_URL` из файла `constants.py` только для вывода в терминал, с какого сайта происходит сбор информации.

Из файла `exceptions.py` мы импортируем наш класс `class ErrArgException` исключения для проверки на ввод не нужной информации для работы программы в команду.

Функция `cmd_parser` используется для определения, какой скрипт нужно запустить - запустить парсинг или очистить таблицу в базе данных.

**`function.py`** - файл, в котором содержатся все функции для работы программы.

```python
import requests_cache
from urllib.parse import urljoin
from tqdm import tqdm
from bs4 import BeautifulSoup
import time
import logging

from sqlalchemy import create_engine, Column, Integer, String, delete
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

#
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем базовый класс
Base = declarative_base()


# Определяем модель для таблицы Recs_Table
class Recs(Base):
    __tablename__ = 'Recs_Table'
    ID = Column(Integer, primary_key=True)
    Title = Column(String)
    Author = Column(String)
    Products = Column(String)
    Description = Column(String)


def clean_db(path_db):
    connection_parameters = 'sqlite:///' + path_db
    engine = create_engine(connection_parameters)
    Base.metadata.create_all(engine)
    session = Session(engine)
    deleter = delete(Recs).where(Recs.id >= 1)
    session.execute(deleter)
    session.commit()
    logger.log('Очистка базы данных')


def write_db(path_db, recs):
    # Создаем соединение с базой данных
    engine = create_engine('sqlite:///' + path_db, echo=True)
    # Создаем таблицу в базе данных (если она еще не существует)
    Base.metadata.create_all(engine)

    # Создаем сессию
    Session = sessionmaker(bind=engine)
    session = Session()

    for rec in recs:
        session.add(rec)

    session.commit()

    # Закрываем сессию
    session.close()


'''
ID
Title
Author
Products
Description
'''


def parsing(main_url, base_url, delay):
    logger.info("Начало парсинга")
    recs = []
    session = requests_cache.CachedSession()
    response = session.get(main_url)
    soup = BeautifulSoup(response.text, features='lxml')
    div_recipe = soup.find('div', attrs={'class': 'recipe_list_new'})
    div_recipes = div_recipe.find_all('div', attrs={'class': 'recipe_l in_seen v2'})

    logger.info("Добавление ссылок на рецепты с текущей страницы")
    urls_child = []
    for recipe in tqdm(div_recipes):
        urls_child.append(urljoin(base_url, recipe.find('a', attrs={'itemprop': 'url'})['href']))

    # собираем ссылки на рецепты с текущей страницы и переходим к следующей
    while True:
        div_page_selector = soup.find('table', attrs={'class': 'page_selector'})
        a_page = div_page_selector.find_all('a')

        next_page = ""
        for a in a_page:
            if "Следующая" in a.text:
                next_page = a['href']
        if next_page == "":
            break
        logger.info("Следующая страница для парсинга: " + next_page)

        url = urljoin(base_url, next_page)
        response = session.get(url)
        soup = BeautifulSoup(response.text, features='lxml')

        div_recipe = soup.find('div', attrs={'class': 'recipe_list_new'})
        if not div_recipe:
            break
        div_recipes = div_recipe.find_all('div', attrs={'class': 'recipe_l in_seen v2'})

        logger.info("Добавление ссылок на рецепты с текущей страницы")
        for recipe in tqdm(div_recipes):
            urls_child.append(urljoin(base_url, recipe.find('div', attrs={'class': 'title'}).find("a")['href']))
        time.sleep(delay)

    logger.info("Парсинг всех рецептов")
    for url in urls_child:
        logger.info("Рецепт: " + url)
        time.sleep(delay)
        response = session.get(url)
        soup = BeautifulSoup(response.text, features='lxml')
        h_title = soup.find('h1', attrs={'class': 'title'})
        if not h_title:
            continue
        # print(h_title.text.replace("\n", ""))
        logger.info("Парсинг заголовка")
        title = h_title.text.replace("\n", "")

        logger.info("Парсинг автора")
        div_user = soup.find('div', attrs={'class': 'el user_date'})
        # print("Автор:", div_user.text.replace("\n", ""))
        author = div_user.text.replace("\n", "")

        products = ""
        logger.info("Парсинг продуктов")
        table_ingr = soup.find('table', attrs={'class': 'ingr'})
        for ingr in table_ingr:
            # print(ingr.text.replace("\n", ""))
            products += ingr.text.replace("\n", "") + "\n"

        logger.info("Парсинг описания рецепта")
        description = ""
        # если рецепт не по фото

        div_recipe_how = soup.find('div', attrs={'id': 'how'})
        p_recipes = div_recipe_how.find_all('p')
        if p_recipes[0].text != "":
            logger.info("Рецепт не по фото")
            for p_recipe in p_recipes:
                # print(p_recipe.text.replace("\n", ""))
                description += p_recipe.text.replace("\n", "") + "\n"

        # если рецепт с фото

        div_images_n = soup.find('div', attrs={'class': 'step_images_n'})
        if div_images_n:
            logger.info("Рецепт по фото")
            for step in div_images_n:
                # print(step.text.replace("\n", ""))
                description += step.text.replace("\n", "") + "\n"

        recs.append(Recs(Title=title, Author=author, Products=products, Description=description))
    return recs
```

Используется для настраивания логирования:
```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

Создаём класс базы данных:
```python
Base = declarative_base()
```

Этот класс искользуется для создания вида таблицы - как будет называться таблица, какие столбцы будут как называться и какие элементы будут в них находиться. 
```python
class Recs(Base):
    __tablename__ = 'Recs_Table'
    ID = Column(Integer, primary_key=True)
    Title = Column(String)
    Author = Column(String)
    Products = Column(String)
    Description = Column(String)
```
`__tablename__` - название таблицы. 

`ID` - номер рецепта в таблице(является primary key).

`Title` - название блюда.

`Author` - автор рецепта.

`Products` - продукты, нужные для приготовления блюда.

`Description` - инструкция приготовления.

```python
def clean_db(path_db):
    connection_parameters = 'sqlite:///' + path_db
    engine = create_engine(connection_parameters)
    Base.metadata.create_all(engine)
    session = Session(engine)
    deleter = delete(Recs).where(Recs.id >= 1)
    session.execute(deleter)
    session.commit()
    logger.log('Очистка базы данных')
```
Функция `clean_db` используется для очистри базы данных. В эту функцию мы передаём название БД, которую мы хотим удалить. После окончания работы программы происходит логирование, которое выдаёт информацию `Очистка базы данных`.

```python
def write_db(path_db, recs):
    engine = create_engine('sqlite:///' + path_db, echo=True)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    for rec in recs:
        session.add(rec)

    session.commit()

    session.close()
```
Функция `write_db` используется для заполнения таблицы используя заранее собранной информации с сайта. В эту функцию мы передаём название файла в котором находится БД и информацию(`path_db` полученную из файла константы и `recs` - другими словами составленные строчки таблицы, созданные вовремя работы программы).

```python 
def parsing(main_url, base_url, delay):
    logger.info("Начало парсинга")
    recs = []
    session = requests_cache.CachedSession()
    response = session.get(main_url)
    soup = BeautifulSoup(response.text, features='lxml')
    div_recipe = soup.find('div', attrs={'class': 'recipe_list_new'})
    div_recipes = div_recipe.find_all('div', attrs={'class': 'recipe_l in_seen v2'})

    logger.info("Добавление ссылок на рецепты с текущей страницы")
    urls_child = []
    for recipe in tqdm(div_recipes):
        urls_child.append(urljoin(base_url, recipe.find('a', attrs={'itemprop': 'url'})['href']))

    # собираем ссылки на рецепты с текущей страницы и переходим к следующей
    while True:
        div_page_selector = soup.find('table', attrs={'class': 'page_selector'})
        a_page = div_page_selector.find_all('a')

        next_page = ""
        for a in a_page:
            if "Следующая" in a.text:
                next_page = a['href']
        if next_page == "":
            break
        logger.info("Следующая страница для парсинга: " + next_page)

        url = urljoin(base_url, next_page)
        response = session.get(url)
        soup = BeautifulSoup(response.text, features='lxml')

        div_recipe = soup.find('div', attrs={'class': 'recipe_list_new'})
        if not div_recipe:
            break
        div_recipes = div_recipe.find_all('div', attrs={'class': 'recipe_l in_seen v2'})

        logger.info("Добавление ссылок на рецепты с текущей страницы")
        for recipe in tqdm(div_recipes):
            urls_child.append(urljoin(base_url, recipe.find('div', attrs={'class': 'title'}).find("a")['href']))
        time.sleep(delay)

    logger.info("Парсинг всех рецептов")
    for url in urls_child:
        logger.info("Рецепт: " + url)
        time.sleep(delay)
        response = session.get(url)
        soup = BeautifulSoup(response.text, features='lxml')
        h_title = soup.find('h1', attrs={'class': 'title'})
        if not h_title:
            continue
        # print(h_title.text.replace("\n", ""))
        logger.info("Парсинг заголовка")
        title = h_title.text.replace("\n", "")

        logger.info("Парсинг автора")
        div_user = soup.find('div', attrs={'class': 'el user_date'})
        # print("Автор:", div_user.text.replace("\n", ""))
        author = div_user.text.replace("\n", "")

        products = ""
        logger.info("Парсинг продуктов")
        table_ingr = soup.find('table', attrs={'class': 'ingr'})
        for ingr in table_ingr:
            # print(ingr.text.replace("\n", ""))
            products += ingr.text.replace("\n", "") + "\n"

        logger.info("Парсинг описания рецепта")
        description = ""
        # если рецепт не по фото

        div_recipe_how = soup.find('div', attrs={'id': 'how'})
        p_recipes = div_recipe_how.find_all('p')
        if p_recipes[0].text != "":
            logger.info("Рецепт не по фото")
            for p_recipe in p_recipes:
                # print(p_recipe.text.replace("\n", ""))
                description += p_recipe.text.replace("\n", "") + "\n"

        # если рецепт с фото

        div_images_n = soup.find('div', attrs={'class': 'step_images_n'})
        if div_images_n:
            logger.info("Рецепт по фото")
            for step in div_images_n:
                # print(step.text.replace("\n", ""))
                description += step.text.replace("\n", "") + "\n"

        recs.append(Recs(Title=title, Author=author, Products=products, Description=description))
    return recs
```

Функция `parsing` используется для парсинга сайта, ссылку на который мы берём из файла `constants.py`. В функцию у нас передаётся ссылка на основной сайт, ссылка на сайт с рецептами запеканок и время задержки. При запуске функции сробатывает логирование и предупреждает, что началась работа данного скрипта. 

Как работает функция:
1) создаётся массив `recs`, в который будут добавляться получившиеся строчки для таблицы, после окончания работы скрипта.
2) созадётся сессия, благодаря библиотеке `requests_cache`
3) начинаем работы с ссылкой, которую мы получили из файла `constants.py`, то есть получаем код страницы и начинаем, "гуляя по классам", собирать не достающий врагмент ссылки, чтобы перейти к дальнейшему парсингу(о чём мы уведомим благодаря логированию). 
4) добавим ссылку в массив этиз ссылок
5) после сбора всех ссылок со страницы, переходим на следующую страницу, на которой будут тоже находиться ссылки на рецепты, которые тоже надо собрать
6) после того как мы получили все ссылки на рецепты начинаем переходить по ним и собирать нам нужную информацию(название рецепта, автор и тд)
7) после того, как мы собрали информацию с одной ссылки, мы передаём полученную информацию в массив в виде строчки для таблицы и продолжаем работу функции, пока не закончатся ссылки
8) передаём полученный массив в функцию `write_db` и собираем таблицу 

```python 
from constants import *
from functions import *
from argparser import *
import logging

base_url = BASE_URL
main_url = MAIN_URL
path_db = PATH_DB

if __name__ == '__main__':
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
```
Файл `main.py` является основным файлом, в который мы импортируем `constants.py`, `functions.py` и `argparser.py`, чтобы объединить все эти файлы.

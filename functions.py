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

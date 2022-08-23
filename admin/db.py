# TODO: ADD MUCH MORE ERROR HANDLING
# TODO: MAYBE ADD REQUIRED AGE AND RELEASE YEAR TO THE DATABASE
import sys
import json
import time
import requests
import subprocess
import steamcharts
import csv
import spider
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.errors
import pandas as pd
import os

# connect to database
def connect(name, usr, pwd, my_host, my_port):
    connection = None
    try:
        connection = psycopg2.connect(database=name, user=usr, password=pwd, host=my_host, port=my_port)
        print('Connection successful')
    except psycopg2.OperationalError:
        print('Error connecting')
    return connection

# run sql query
def execute_query(connection, query, fetch=False):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()

    if fetch:
        return cursor.fetchall()

def csv_dump(connection):
    cursor = connection.cursor()
    try:
        query = '''select appid, game_name, price, sale_price, string_agg(distinct(developer_name), ',') as developers, string_agg(distinct(publisher_name), ',') as publishers, string_agg(distinct(tag_name), ',') as tags, string_agg(distinct(genre_name), ',') as genres from games natural join developers natural join tags natural join genres natural join publishers group by appid order by cast(appid as int);'''
        cursor.execute(query)
        connection.commit()
    except psycopg2.errors.Error as e:
        print('fetch error')
        sys.exit(0)

# crawls steamcharts website to pull the first 300 pages (7500 games) which takes about 13 seconds
# not our fault that it's so slow, the site just has poor response time
def scrape_store_page():
    subprocess.run('scrapy runspider steamcharts.py --nolog')

def get_all_games():
    st = set()
    fst = True
    #with open('recdata_new.csv') as f:
    #    foo = csv.reader(f, delimiter=',')
    #    for row in foo:
    #        if fst:
    #            fst = False
    #        else:
    #            st.add(row[2])
    fst = True
    with open('recdata.csv', 'r') as f:
        foo = csv.reader(f, delimiter=',')
        for row in foo:
            if fst:
                fst = False
            else:
                st.add(row[2])
    return st

# updates database with only new entries to it
def update_db(connection):
    # get everything in db
    curr_games = set([x[0] for x in execute_query(connection, 'select appid from games', fetch=True)])
    all_games = set(get_all_games())
    appids = all_games.difference(curr_games)
    get_app_details(appids)
    put_in_db(connection, appids)

# completely refreshes the database
def rebuild_db(connection):
    pass 

# extracts the appid of the top 7500 games on steam
def get_top_games():
    appids = []
    # gets top 300 pages 
    for i in range(1, 301):
        with open(f'eachgame/{i}.html', encoding='utf8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            for link in soup.find_all('td', class_='game-name left'):
                link = link.find('a')
                if link['href'].split('/')[-1] == '550' or link['href'].split('/')[-1] == '400':
                    print('left4dead')
                appids.append(link['href'].split('/')[-1])

    return appids

# gets the app details for the top 7500 games on steam
def get_app_details(appids):
    proc = CrawlerProcess()
    proc.crawl(spider.Scraper, appids)
    proc.start()

def init_db(connection):
    # TODO: ADD SENTIMENT AND EARLY ACCESS
    games_attrs = '''appid VARCHAR(7) PRIMARY KEY,
    game_name VARCHAR(256),
    price DECIMAL(6,2),
    sale_price DECIMAL(6,2),
    metascore SMALLINT
    '''
    publishers_attrs = '''appid VARCHAR(7) REFERENCES games(appid),
    publisher_name VARCHAR(256),
    PRIMARY KEY(appid, publisher_name)
    '''
    genres_attrs = '''appid VARCHAR(7) REFERENCES games(appid),
    genre_name VARCHAR(128),
    PRIMARY KEY(appid, genre_name)
    '''
    tags_attrs = '''appid VARCHAR(7) REFERENCES games(appid),
    tag_name VARCHAR(128),
    PRIMARY KEY(appid, tag_name)'''

    developers_attrs = '''appid VARCHAR(7) REFERENCES games(appid),
    developer_name VARCHAR(256),
    PRIMARY KEY(appid, developer_name)
    '''

    execute_query(connection, f'CREATE TABLE IF NOT EXISTS games({games_attrs})')
    execute_query(connection, f'CREATE TABLE IF NOT EXISTS publishers({publishers_attrs})')
    execute_query(connection, f'CREATE TABLE IF NOT EXISTS genres({genres_attrs})')
    execute_query(connection, f'CREATE TABLE IF NOT EXISTS tags({tags_attrs})')
    execute_query(connection, f'CREATE TABLE IF NOT EXISTS developers({developers_attrs})')
    
def put_in_db(connection, appids):
    for appid in appids:
        try:
            with open(f'tmp/{appid}.json', encoding='utf8') as f:
                game = json.loads(f.read())[appid]

                # some games don't have details in the steam api and return a failure state when we try to get them
                if game['success']:
                    data = game['data']

                    # some entries are demos, DLC, mods, etc. so we don't wish to include them
                    if data['type'] != 'game':
                        continue
                    game_name = data['name'].replace("'", "''") # escapes apostrophe in games like "Assassin's Creed"
                    publishers = data['publishers']
                    #early_access = data['early_access']
                    # FIXME: CHECK IF THIS EXISTS, BECAUSE NOT ALL PAGES HAVE IT
                    genres = data['genres'] if 'genres' in data else []
                    categories = data['categories'] if 'categories' in data else []
                    metacritic = data['metacritic']['score'] if 'metacritic' in data else None
                    #release_date = data['release_date'] if 'release_date' in data else None
                    developers = data['developers'] if 'developers' in data else []
                    price = data['price_overview'] if 'price_overview' in data else None
                    currency = price['currency'] if price else None
                    initial = price['initial'] if price else 0
                    final = price['final'] if price else 0

                    if currency and currency != 'USD':
                        # FIXME: JUST PUT THE CURRENCY IN AS NULL
                        initial = None
                        final = None

                    # FIXME: ADD IN RELEASE DATE
                    #if release_date:
                    #    release_date = 
                    #    mon_day, year = release_date.split(', ')
                    #    mon, day = mon_day.split(' ')

                    #    mon_to_num = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                    #    release_date = f'{year}-{mon_to_num[mon]}-{day}'

                    if initial:
                        initial = int(initial)/100
                    else:
                        initial = 'NULL'
                    
                    if final:
                        final = int(final)/100
                    else:
                        final = 'NULL'

                    if not metacritic:
                        metacritic = 'NULL'
                    else:
                        metacritic = int(metacritic)

                    execute_query(connection, f"""INSERT INTO games(appid, game_name, price, sale_price, metascore) VALUES ('{appid}', '{game_name}', {initial}, {final}, {metacritic});""")

                    for publisher in publishers:
                        publisher = publisher.replace("'", "''")
                        execute_query(connection, f"INSERT INTO publishers(appid, publisher_name) VALUES ('{appid}', '{publisher}')")
                    for developer in developers:
                        developer = developer.replace("'", "''")
                        execute_query(connection, f"INSERT INTO developers(appid, developer_name) VALUES ('{appid}', '{developer}')")
                    for tag in categories:
                        tag = tag['description']
                        # FIXME: STEAM WORKSHOP IS KNOWN TO APPEAR MULTIPLE TIMES IN SOME GAMES DESCRIPTOINS
                        # SOLUTION: TO USE THE ID INSTEAD OF DESCRIPTION OR TO CHECK IF STEAM WORKSHOP IS IN TEH TAGS TABLE
                        if tag != 'Steam Workshop':
                            execute_query(connection, f"INSERT INTO tags(appid, tag_name) VALUES ('{appid}', '{tag}')")
                    for genre in genres:
                        genre = genre['description']
                        execute_query(connection, f"INSERT INTO genres(appid, genre_name) VALUES ('{appid}', '{genre}')")
        except FileNotFoundError:
            print('FILE NOT FOUND')
        except psycopg2.errors.Error as e:
            print(f'Error: {e}')
            print(f'Game: {appid}')
            connection = connect('steam', 'postgres', '$Jackface1!', '127.0.0.1', '5432')

def load_db(connection):
    cursor = connection.cursor()

def drop_db(connection):
    execute_query(connection, 'DROP TABLE GAMES CASCADE')
    execute_query(connection, 'DROP TABLE DEVELOPERS CASCADE')
    execute_query(connection, 'DROP TABLE GENRES CASCADE')
    execute_query(connection, 'DROP TABLE TAGS CASCADE')
    execute_query(connection, 'DROP TABLE PUBLISHERS CASCADE')


def test():
    appids = get_top_games()
    print('got games')
    connection = connect('steam', 'postgres', '$Jackface1!', '127.0.0.1', '5432')
    #drop_db(connection)
    #init_db(connection)
    #put_in_db(connection, appids)
    appids = []
    with open('gets.csv') as f:
        for line in f.readlines():
            if line.strip() != ',id':
                line = line.split(',')[1].strip()
                #print(line)
                cursor = connection.cursor()
                cursor.execute(f"select appid from games where appid='{line}'")
                if not cursor.fetchone():
                    appids.append(line)
            else:
                print('trigger')

    get_app_details(appids)
    put_in_db(connection, appids)
    #csv_dump(connection)

def test2():
    # FIXME: CAN HAVE AN ISSUE WHERE OUR ORIGINAL CONNECTION IS NO LONGER VALID BUT WE DON'T KNOW ABOUT IT
    connection = connect('steam', 'postgres', '$Jackface1!', '127.0.0.1', '5432')
    #drop_db(connection)
    #init_db(connection)

    appids = None
    for x, y, filenames in os.walk('./tmp'):
        appids = [fname.split('.')[0] for fname in filenames]

    drop_db(connection)
    init_db(connection)
    put_in_db(connection, appids)

if __name__ == '__main__':
    test2()
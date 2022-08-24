# TODO: TIDY THIS FILE UP, IT'S A MESS OF UNUSED FUNCTIONS AND DUPLICATED FUNCTIONALITY AS WELL AS STUFF UNRELATED TO DB
import json
import subprocess
import csv
import os

import psycopg2
import psycopg2.errors
import spider
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup

def connect(name, usr, pwd, my_host, my_port):
    '''Connect to postgres db
    
    Parameters
    ----------
    name : str
        database name
    usr : str
        username
    pwd : str
        password
    my_host : str
        ip_addr to connect to database on
    my_port : int
        port to connect to database on

    Returns
    -------
    psycopg2.connection
        connection to the postgres db 
    '''
    connection = None
    try:
        connection = psycopg2.connect(database=name, user=usr, password=pwd, host=my_host, port=my_port)
        print('Connection successful')
    except psycopg2.OperationalError:
        print('Error connecting')
    return connection

def execute_query(connection, query, fetch=False):
    '''Executes query on db connection and returns results if fetch is True
    
    Parameters
    ----------
    connection : psycopg2.connection
        connection to the postgres db
    query : str
        sql query to execute
    fetch : bool, optional
        tells whether or not to return results of the query

    Returns
    -------
    object
        results of the sql query
    None
        if fetch is false
    '''
    # TODO: ADD ERROR HANDLING
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()

    if fetch:
        return cursor.fetchall()

def scrape_store_page():
    '''Runs the spider that scrapes the steamcharts site'''
    # TODO: FIGURE OUT HOW TO RUN TWO OF THE SCRAPYS THE NORMAL WAY INSTEAD OF HAVING TO RUN ONE IN SUBPROCESS
    #       BECAUSE OF TWISTER ERRORS
    subprocess.run('scrapy runspider steamcharts.py --nolog')

def get_all_games():
    '''gets all games in the existing dataset
    
    Returns
    -------
    set
        set of appids of all games in the existing dataset

    Raises
    ------
    FileNotFoundError
        occurs if we can't find the dataset file
    '''
    # Get unique appid from existing dataset
    st = set()
    fst = True
    with open('api/recdata_new.csv') as f:
        foo = csv.reader(f, delimiter=',')
        for row in foo:
            if fst:
                fst = False
            else:
                st.add(row[2])
    return st

def update_db(connection):
    '''Updates database with all of the games in our training dataset not in our database
    
    Parameters
    ----------
    connection : psycopg2.connection
        connection to the database
    '''    

    # put everything from the existing dataset that we haven't put in the db into the db
    curr_games = set([x[0] for x in execute_query(connection, 'select appid from games', fetch=True)])
    all_games = set(get_all_games())
    appids = all_games.difference(curr_games)
    get_app_details(appids)
    put_in_db(connection, appids)

def rebuild_db(connection):
    '''Wipes database and refreshes it from scratch
    
    Parameters
    ----------
    connection : psycopg2.connection
        connection to database
    '''
    # TODO: IMPLEMENT FUNCTIONALITY
    pass 

def get_top_games():
    '''Gets the appids from the steamcharts HTML files we scraped

    Returns
    -------
    list
        the top 7500 games on steam

    Raises
    ------
    FileNotFoundError
        can't find the file for a webpage we should have downloaded
    '''
    appids = []
    # gets top 300 pages 
    for i in range(1, 301):
        with open(f'eachgame/{i}.html', encoding='utf8') as f:
            # The appid is located in an <a> tag nested in a <td> tag
            soup = BeautifulSoup(f, 'html.parser')
            for link in soup.find_all('td', class_='game-name left'):
                link = link.find('a')
                appids.append(link['href'].split('/')[-1])
    return appids

def get_app_details(appids):
    '''Gets the app details for the given appids
    
    Parameters
    ----------
    appids : list of str
        list of appids to get app details for
    '''
    proc = CrawlerProcess()
    proc.crawl(spider.Scraper, appids)
    proc.start()

def init_db(connection):
    '''Creates the database
    
    Parameters
    ----------
    connection : psycopg2.connection
        connection to postgres db
    '''
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
    '''Puts the app details for the given appids into the database
    
    Parameters
    ----------
    connection : psycopg2.connection
        connection to database
    appids : list of str
        list of appids of games to put in the database
    '''
    # TODO: ADD ERROR HANDLING
    for appid in appids:
        try:
            # FIXME: THIS WON'T WORK ANYMORE
            with open(f'tmp/{appid}.json', encoding='utf8') as f:
                game = json.loads(f.read())[appid]

            # Load db info in case of necessary reconnect
            db_name = usr = pwd = host = port = None
            with open('db_info.txt', 'r') as f:
                db_name, usr, pwd, host, port = f.readlines()

                # some games don't have details in the steam api and return a failure state when we try to get them
                if game['success']:
                    data = game['data']

                    # some entries are demos, DLC, mods, etc. so we don't wish to include them
                    if data['type'] != 'game':
                        continue

                    # Extract the data
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
            connection = connect(db_name, usr, pwd, host, port)

def drop_db(connection):
    '''Wipes the database clean
    
    Warning
    -------
    DO NOT USE THIS FUNCTION UNLESS YOU WANT TO COMPLETELY NUKE THE ENTIRE DATABASE
    
    
    Parameters
    ----------
    connection : psycopg2.connection
        connection to database
    '''
    execute_query(connection, 'DROP TABLE GAMES CASCADE')
    execute_query(connection, 'DROP TABLE DEVELOPERS CASCADE')
    execute_query(connection, 'DROP TABLE GENRES CASCADE')
    execute_query(connection, 'DROP TABLE TAGS CASCADE')
    execute_query(connection, 'DROP TABLE PUBLISHERS CASCADE')

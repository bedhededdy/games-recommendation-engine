from time import sleep
from sys import exit
import json

import scrapy

class user_scraper(scrapy.Spider):
    '''Scrapes the games that the user's in our training data own

    Attributes
    ----------
    name : str
        A name that allows scrapy to recognize this Spider when being run from the terminal/subprocess module

    Methods
    -------
    start_requests()
        Makes the requests to get the owned games of each user in our training data
    limit(response)
        Sleeps for an hour if we get blocked for too many requests
    parse(response)
        Writes each user's data to a json file
    '''
    name = 'user'

    def start_requests(self):
        '''Makes the requests to get the owned games of each user in our training data

        Yields
        -----
        scrapy.Request
            yields API JSON request for user library
        
        Raises
        ------
        FileNotFoundError
            usrdata.json or key.txt don't exist
        KeyError
            dummy key doesn't exist in users
        Exception
            something goes wrong during scraping
        '''
        # FIXME: THIS NEEDS TO USE A DIFFERENT FILE, BECAUSE USRDATA.JSON DOESN'T EXIST ANYMORE
        # Load necessary data from disk
        users = None
        with open('usrdata.json', 'r') as f:
            users = json.load(f)
        
        key = None
        with open('key.txt', 'r') as f:
            key = f.read()

        # Request library for each user
        for dictionary in users['dummy']:
            try:
                yield scrapy.Request(url=f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={dictionary['steam_id']}&format=json&include_free_played_games=1", callback=self.parse, errback=self.limit)
            except Exception:
                print('Rate Limited')
                exit(0)
            
    def limit(self, response):
        '''Sleeps if we get blocked for too many requests
        
        Parameters
        ----------
        response : ?
            holds the problematic response returned by scrapy
        '''
        print(f'Error: {response.status}')

        # RATE LIMIT: WAIT FOR 1 HOUR
        self.crawler.engine.pause()
        sleep(3600)
        self.crawler.engine.unpause()

    def parse(self, response):
        '''Writes each user's data to a json file
        Parameters
        ----------
        response : ?
            holds the json response with the user's library
        
        Raises
        ------
        FileNotFoundError
            user directory doesn't exist
        '''
        usr = response.url.split('steamid=')[1].split('&')[0]
        with open(f'user/{usr}.json', 'wb') as f:
            f.write(response.body)


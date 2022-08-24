from time import sleep
from sys import exit

import scrapy

# TODO: RENAME THIS CLASS
class Scraper(scrapy.Spider):
    '''Scrapes the Steam API for more detailed information about a given appid

    Attributes
    ----------
    name : str
        A name that allows scrapy to recognize this Spider when being run from the terminal/subprocess module
    appids : list of str
        A list containing all the appids we want to scrape info about
    requests : int
        Counts the number of requests we have made thus far to the API

    Methods
    -------
    start_requests()
        Makes the requests for each appid to the Steam API
    parse()
        Writes results of an API call to file
    '''
    name = 'app_details_scraper'
    
    def __init__(self, appids):
        '''Constructs spider with the necessary metadata
        
        Parameters
        ----------
        appids : list of str
            A list containing all the appids we want to scrape info about
        '''
        super().__init__()
        self.appids = appids
        self.requests = 0

    def start_requests(self):
        '''Makes the requests for each appid to the Steam API

        Parameters
        ----------
        None

        Yields
        ------
        scrapy.Request
            A request object that contains a JSON response with our app details in it

        Raises
        ------
        Exception
            Occurs when we are rate limited by Steam and our IP is blocked
        '''
        # Get app details for each appid given to us
        for appid in self.appids:
            try:
                yield scrapy.Request(url=f'https://store.steampowered.com/api/appdetails?appids={appid}', callback=self.parse)
            except Exception:
                # TODO: Should figure out what the actual exception is called and replace it above
                print('Rate Limit Failed...\nCritical Error...\nExiting...')
                exit(0)

            self.requests += 1

            # TODO: YOU SHOULD USE A BETTER WAY TO RATE LIMIT YOUR REQUESTS
            # Rate Limit ourselves to 40 requests a minute so Steam doesn't block our IP
            if self.requests % 40 == 0:
                self.crawler.engine.pause()
                sleep(60)
                self.crawler.engine.unpause()

    def parse(self, response):
        '''Writes results of an API call to file
        
        Parameters
        ----------
        response : ?
            Contains the app details in JSON format returned by the scrapy request

        Raises
        ------
        FileNotFoundError
            Occurs if tmp directory does not exist 
        '''
        # Write JSON to file with name {appid}.json  
        page = response.url.split('=')[-1]
        fname = f'tmp/{page}.json'
        with open(fname, 'wb') as f:
            f.write(response.body)
        
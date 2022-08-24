import scrapy

# TODO: ADD SOME ERROR HANDLING
class SteamChartsScraper(scrapy.Spider):
    '''Scrapes the top 7500 most played games right now from steamcharts.com
    
    Attributes
    ----------
    name : str
        A name to identify the spider to scrapy from the command line and subprocess module
        
    Methods
    -------
    start_requests()
        Get 300 pgs. (7500 games) of the most popular games right now on Steam
    parse(response)
        Write each page to a file to be operated on later
    '''
    name = 'steam_charts_scraper'
    
    def start_requests(self):
        '''Get 300 pgs. (7500 games) of the most popular games right now on Steam

        Yields
        ------
        scrapy.Request
            yields HTML response containing 75 games

        Raises
        ------
        Exception
            exception occurred when scraping
        '''
        for i in range(1, 301):
            yield scrapy.Request(url=f'https://steamcharts.com/top/p.{i}', callback=self.parse)

    def parse(self, response):
        '''Write each page to a file to be operated on later

        Parameters
        ----------
        response : ?
            Response returned by the scrapy request

        Raises
        ------
        FileNotFoundError
            eachgame folder doesn't exist
        '''
        # Write each page to an HTML file
        page = response.url.split('.')[-1]
        fname = f'eachgame/{page}.html'
        with open(fname, 'wb') as f:
            f.write(response.body)
        
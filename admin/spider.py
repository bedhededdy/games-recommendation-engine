from time import sleep
import scrapy
import sys

class Scraper(scrapy.Spider):
    name = 'steam_scraper'
    
    def __init__(self, appids):
        super().__init__()
        self.appids = appids
        self.requests = 0

    def start_requests(self):
        for appid in self.appids:
            try:
                yield scrapy.Request(url=f'https://store.steampowered.com/api/appdetails?appids={appid}', callback=self.parse)
            except:
                print('RATE LIMITED')
                sys.exit(0)

            self.requests += 1

            # TODO: YOU SHOULD USE A BETTER WAY TO RATE LIMIT YOUR REQUESTS
            if self.requests % 40 == 0:
                self.crawler.engine.pause()
                sleep(60)
                self.crawler.engine.unpause()

    def parse(self, response):
        page = response.url.split('=')[-1]
        fname = f'tmp/{page}.json'
        with open(fname, 'wb') as f:
            f.write(response.body)
        
from time import sleep
import scrapy
import json
import sys

class user_scraper(scrapy.Spider):
    name = 'user'

    def start_requests(self):
        users = None
        with open('usrdata.json', 'r') as f:
            users = json.load(f)
        
        key = None
        with open('key.txt', 'r') as f:
            key = f.read()

        for dictionary in users['dummy']:
            # NOTE: WE DO NOT NEED TO RATE LIMIT THIS BECAUSE THIS IS LOCKED BEHIND THE API KEY
            #       WE GET 100K API CALLS A DAY AS OPPOSED TO BEING RATE LIMITED TO 200 REQUESTS PER 5 MINS
            #       THIS ALLOWS US TO GET EVERYTHING IN ONE GO
            # NOTE: THIS WILL TAKE AWHILE AS WE ARE MAKING AROUND 90K HTTP REQUESTS
            # NOTE: WE PROBABLY WANNA RATE LIMIT AT AROUND EACH 50K FOR ABOUT MAYBE 30 MINS 
            #       DOING STUFF ASAP ACTUALLY GIVES A 429
            try:
                yield scrapy.Request(url=f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={dictionary['steam_id']}&format=json&include_free_played_games=1", callback=self.parse, errback=self.limit)
            except Exception:
                print('Rate Limited')
                sys.exit(0)
            
    def limit(self, response):
        print(f'Error: {response.status}')

        # RATE LIMIT: WAIT FOR 1 HOUR
        self.crawler.engine.pause()
        sleep(3600)
        self.crawler.engine.unpause()

    def parse(self, response):
        # TODO: you can optimize this
        usr = response.url.split('steamid=')[1].split('&')[0]
        with open(f'user/{usr}.json', 'wb') as f:
            f.write(response.body)


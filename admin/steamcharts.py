import scrapy

# NOTE: TAKES ABOUT 16 SECONDS TO RUN, NOT BECAUSE OF POOR CODE BUT BECAUSE 
#       THE SITE IS SLOW. WE KNOW THIS BECAUSE WE CAN GET MUCH MORE DATA FROM STEAM
#       MUCH MORE QUICKLY
class SteamChartsScraper(scrapy.Spider):
    name = 'steam_charts_scraper'
    
    def __init__(self):
        super().__init__()
        self.appids = [str(i) for i in range(1, 301)]

    def start_requests(self):
        for appid in self.appids:
            yield scrapy.Request(url=f'https://steamcharts.com/top/p.{appid}', callback=self.parse)

    def parse(self, response):
        # TODO: WOULD BE BETTER TO JUST UPLOAD FROM HERE DIRECTLY TO THE DATABASE
        page = response.url.split('.')[-1]
        fname = f'eachgame/{page}.html'
        # FIXME: NOT ACTUALLY BEING WRITTEN AS BINARY
        # Might be worse to encode as binary string only to have to decode again
        # only worth it to do if bad perform
        with open(fname, 'wb') as f:
            f.write(response.body)
        
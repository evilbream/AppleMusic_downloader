import json
import requests
from bs4 import BeautifulSoup
import logging
import aiohttp
import asyncio
from collections import namedtuple

ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
headers = {
    "User-Agent": ua, "Accept-Language": "en-US, en;q=0.5", 'Content-Type': 'application/json; charset=utf-8'}

logging.basicConfig(level=logging.INFO)


class Apple_songs:
    def __init__(self, link: str):
        self.link = link
        self.scr = None
        self.request_apple_page()

    def request_apple_page(self):
        try:
            res = requests.get(self.link, headers={'Content-Type': 'application/json; charset=ISO-8859-1'})
            if res.text is not None:
                soup = BeautifulSoup (res.text, 'lxml')
                scr = soup.find ('script', type='application/json')
                if scr:
                    self.scr = scr.text
        except Exception as err:
            print(err)
            return None

    @staticmethod
    def convert_to_seconds(duration: int):
        return int(duration * 0.001)

    def get_data_from_dict(self, song):
        Song = namedtuple('Song', 'name artist duration url')
        match song:
            case {'attributes': {'name': name, 'artistName': artist, 'durationInMillis':duration, 'artwork': {'url': url, 'width': w, 'height': h}}}:
                name = name.encode ('ISO-8859-1', errors='replace').decode ('utf-8', errors='replace')
                artist = artist.encode ('ISO-8859-1', errors='replace').decode ('utf-8', errors='replace')
                return Song(name, artist, self.convert_to_seconds(duration), f"{url.rstrip ('{w}x{h}bb.{f}')}{w}x{h}.jpg")
            case _:
                return None

    def get_songs(self) -> list[tuple] | None:
        if self.scr is None:
            print('No data on this page')
            return None
        js = json.loads (self.scr)
        songs = [self.get_data_from_dict(i) for i in js[0]['data']['seoData']['ogSongs']]
        return songs

    def get_song_in_batch(self, batch_size: int | None = None) -> None|list[tuple[str]]|tuple[str]:
        songs = self.get_songs()
        if (songs is not None) and batch_size is not None:
            songs = [songs[i:i + batch_size] for i in range (0, len (songs), batch_size)]
            return songs
        elif songs is not None:
            for song in songs:
                yield song
        else:
            return songs


async def main(link):
    ls = Apple_songs (link).get_songs() #
    print(ls)
    if ls is None:
        print('Incorrect URL try again')
        return
    #for i in ls: # передаем указанное колличество
        #link = await Search (i).request ()
        #print (link)

link = 'https://music.apple.com/ru/album/v-deluxe/1422651829'

if __name__ == '__main__':
    asyncio.run(main(link))



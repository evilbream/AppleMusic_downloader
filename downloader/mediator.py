from dataclasses import dataclass
from downloader.appe_info import Apple_songs
import aiohttp
from bs4 import BeautifulSoup
import json
import asyncio
from downloader.filter_search_results import Filter

ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
headers = {
    "User-Agent": ua, "Accept-Language": "en-US, en;q=0.5", 'Content-Type': 'application/json; charset=utf-8'}


class Search:  # search links on yt
    def __init__(self, apple_songs: list):
        self.apple_songs = apple_songs  # получен батч файлом от эпл

    async def fetch_data(self, url: str, duration: int, song_name):
        js = None
        async with aiohttp.ClientSession () as session:
            async with session.get (url, headers=headers, timeout=10) as res:
                res = await res.text()
                soup = BeautifulSoup (res, 'lxml')
                js_data = soup.find_all ('script')  #: {'nonce': 'gLZtoAqG-cDgQyk0nHMQnQ'})
                for i in js_data:
                    if 'var ytInitialData' in i.text:
                        js = json.loads(i.text.lstrip ('var ytInitialData = ').rstrip (';'))
            if js is None:
                return None
            video_id, second_id = await Filter(js, duration).video_id
            #print(video_id)
            if not video_id:
                return None
            return f'https://youtu.be/{video_id}', f'{song_name}.mp3', f'https://youtu.be/{second_id}', 0

    async def request(self):
        request = []
        for song in self.apple_songs:
            name = song.name.split (' ')
            artist = song.artist.split (' ')
            url = f"https://www.youtube.com/results?search_query={'+'.join ([*name, *artist])}"
            song_name = '_'.join ([*name, *artist]).replace('*', '')
            request.append(self.fetch_data(url, int(song.duration), song_name))
        res = await asyncio.gather(*request, return_exceptions=True)
        good_requests = [good for good in res if not isinstance(res, Exception)]


        # wait in cycle
        #fetched_links = await asyncio.gather (*request)
        return good_requests


@dataclass
class Mediator:
    APPLE_SONGS: list
    batch_size: int
    first_request: bool = True
    offset: int = 0

    async def get_songs_urls(self, int_songs_redownloaded: int=0):
        download = self.batch_size - int_songs_redownloaded
        songs = self._get_songs_list(download, offset=self.offset)
        self.offset += download
        songs = await Search (songs).request ()
        return songs

    def _get_songs_list(self, num:int, offset: int=0):
        #print(num, offset)
        return self.APPLE_SONGS[offset:num + offset]







import asyncio
import json
import logging
import re
import sys
from urllib.parse import unquote
import time
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from pathlib import Path
from downloader.appe_info import Apple_songs, Search
from utils import Decipher
import aiofiles

ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
headers = {
    "User-Agent": ua, "Accept-Language": "en-US, en;q=0.5", 'Content-Type': 'application/json; charset=utf-8'}

logging.basicConfig(level=logging.INFO)

class Download:
    def __init__(self, urls: list):
        self.urls = urls


    def get_link_dict(self, response):
        bs = BeautifulSoup (response, 'lxml')
        play_response = bs.find_all ('script')
        for i in play_response:
            if 'var ytInitialPlayerResponse = ' in i.text:
                name = i.text.lstrip ('var ytInitialPlayerResponse = ').rstrip(";var meta = document.createElement('meta'); meta.name = 'referrer'; meta.content = 'origin-when-cross-origin'; document.getElementsByTagName('head')[0].appendChild(meta);")
                js = json.loads (name)
                vid_link = js['streamingData']  # all ciphered links to videos
                #print(vid_link['adaptiveFormats'])
                for i in vid_link['adaptiveFormats']:
                    if (i['mimeType'].startswith ('audio/mp4')) and (i['audioQuality'] == 'AUDIO_QUALITY_MEDIUM'):
                        #print (i)
                        return i

        return None

    async def fetch_data(self, session: ClientSession, url: str, song_name: str, second_url) -> tuple | None:
        async with session.get (url, headers=headers) as res:
            res = await res.text ()
            dict_to_decipher = self.get_link_dict(res)
            js_url = 'https://youtube.com/' + re.findall (r'"jsUrl":"(.*?)"', res)[0]
            if "signatureCipher" in dict_to_decipher.keys():
                async with session.get (js_url, headers=headers, timeout=6) as res:

                    js_file = await res.text()
                data = Decipher (js_file, process=True).get_full_function ()
                signature, urls = dict_to_decipher["signatureCipher"].split ('&sp=sig&url=')
                signature = signature.replace ("s=", '', 1).replace ('%253D', '%3D').replace ('%3D', '=')
                deciphered_signature = Decipher ().deciphered_signature (signature, algo_js=data)
                urls = unquote (urls) + '&sig=' + deciphered_signature
                #print (url)
                try:
                    downloaded = await self.download_files(urls, song_name, real_url=url, second_url=second_url)
                    return downloaded
                except TimeoutError:
                    return None
        try:
            downloaded = await self.download_files (dict_to_decipher['url'], song_name, real_url=url, second_url=second_url)
            return downloaded
        except TimeoutError:
            return None

    async def request(self): # returned fetched links
        async with aiohttp.ClientSession () as session:
            request = [self.fetch_data (session, url[0],  url[1], url[2]) for url in self.urls if isinstance(url, tuple)]
            fetched_links = await asyncio.gather (*request, return_exceptions=True)
            print(fetched_links)
            bad_requests = [bad_req for bad_req in fetched_links if isinstance(bad_req, tuple)]
            new = [fetched_links.index (dat) for dat in fetched_links if isinstance (dat, Exception)]
            for num in new:
                bad_requests.append((self.urls[num][2], self.urls[num][1], self.urls[num][0]))
            return bad_requests


    async def download_files(self, url, song_name, real_url, second_url: str):
        print(f'Downloading {song_name}')
        #print(url)
        async with aiohttp.ClientSession() as session:
            async with session.get (url, headers=headers) as res:
                bytes_len = res.content_length # если 0 байтов то надо по новой все запрашивать
                print(f'Bytes: {bytes_len}', song_name)
                if bytes_len > 5000000:
                    print(f'Unable to download {song_name} file is too big, trying another link')
                    return second_url, song_name, second_url
                if bytes_len == 0:
                    return real_url, song_name, real_url
                async with aiofiles.open (Path(Path(__file__).parents[1], 'music', song_name), 'wb') as f:
                    byte = 0
                    try:
                        async for chunk in res.content.iter_chunked (10240):
                            await asyncio.sleep(0)
                            await f.write(chunk)
                            byte += 10240
                            if byte % 102400 == 0:
                                print(f'Downloaded {byte}/{bytes_len} - {song_name}')

                    except Exception as err:
                        print(err)
                        return real_url, song_name, real_url
        return None

async def main(link):
    ls = Apple_songs (link).get_song_in_batch (batch_size=6)
    bad_request = []
    if ls is None:
        print('Try different link')
        sys.exit(0)
    print('Starting to download...')
    for i in ls:
        link = await Search (i).request ()
        print(link)
        if link:
            #print(link)
            timer = time.time ()
            bad_request = await Download(link).request()
            print (f'Elapsed time: {time.time () - timer}')
            await asyncio.sleep(2)
        if bad_request:
            print(f'Trying to download again: {", ".join([bad[1] for bad in bad_request])}')
            await Download (bad_request).request ()
        bad_request = []

if __name__ == '__main__':
    pass



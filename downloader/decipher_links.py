import asyncio
import functools
import json
import logging
import re
import sys
from urllib.parse import unquote
import time
import aiohttp
import requests
from aiohttp import ClientSession, ClientResponse
from bs4 import BeautifulSoup
from pathlib import Path
from downloader.appe_info import Apple_songs
from downloader.mediator import Mediator
from utils import Decipher
import aiofiles
from concurrent.futures import ThreadPoolExecutor

ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
headers = {
    "Accept-Language": "en-US, en;q=0.5", 'Content-Type': 'application/json; charset=utf-8'}

logging.basicConfig(level=logging.INFO)

class Download:
    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    def get_link_dict(self, response):
        bs = BeautifulSoup (response, 'lxml')
        play_response = bs.find_all ('script')
        for i in play_response:
            if 'var ytInitialPlayerResponse = ' in i.text:
                name = i.text.lstrip ('var ytInitialPlayerResponse = ').rstrip(";")
                js = json.loads (name)
                #print(js)
                try:
                    vid_link = js['streamingData']  # all ciphered links to videos
                except KeyError:
                    return None
                #print(vid_link['adaptiveFormats'])
                for i in vid_link['adaptiveFormats']:
                    if (i['mimeType'].startswith ('audio/mp4')) and (i['audioQuality'] == 'AUDIO_QUALITY_MEDIUM'):
                        #print (i)
                        return i

        return None

    async def decipher_urls(self, url: str, song_name: str, second_url, tries: int):
        async with aiohttp.ClientSession () as session:
            async with session.get (url, headers=headers, timeout=7) as res:
                res = await res.text ()
                dict_to_decipher = self.get_link_dict(res)
                if dict_to_decipher is None:
                    data = await self.decipher_urls(second_url, song_name, second_url, tries)
                    return data
                js_url = 'https://youtube.com/' + re.findall (r'"jsUrl":"(.*?)"', res)[0]
                if "signatureCipher" in dict_to_decipher.keys():
                    async with session.get (js_url, headers=headers, timeout=7) as res:

                        js_file = await res.text()
                        #print(js_file)
                    data = Decipher (js_file, process=True).get_full_function ()
                    #print(data)
                    signature, urls = dict_to_decipher["signatureCipher"].split ('&sp=sig&url=')
                    signature = signature.replace ("s=", '', 1).replace ('%253D', '%3D').replace ('%3D', '=')
                    deciphered_signature = Decipher ().deciphered_signature (signature, algo_js=data)
                    urls = unquote (urls) + '&sig=' + deciphered_signature
                    #print(urls)
                    return urls, song_name, second_url, url, tries

        return dict_to_decipher['url'], song_name, second_url, url, tries

    async def decipher_helper(self, urls):
            # request links to desipher
            request = await asyncio.gather(*[self.decipher_urls (url[0],  url[1], url[2], url[3]) for url in urls if isinstance(url, tuple)], return_exceptions=True)
            good = [req for req in request if isinstance(req, tuple)]
            bad = [req for req in request if not isinstance(req, tuple)]
            return good, bad


    async def request(self): # returned fetched links
        urls = await self.mediator.get_songs_urls()
        while urls:
            good, bad = await self.decipher_helper(urls)
            song_names = [gd[1] for gd in good]
            #print(bad)
            #print(song_names, '\n\n')
            if bad:
                print('Requesting deciphering again, some error occeured')
                await asyncio.sleep(1)
                new_urls = [url for url in urls if url[1] not in song_names]
                #print(new_urls)
                new_good, bad = await self.decipher_helper (new_urls)
                good += new_good
            # скачать файл и если ничего не вышло сдать сколько надо медиаоторов

            #print(good)



            download = await asyncio.gather(*[self.download_files(url[0], url[1], url[2], url[3], url[4]) for url in good])
            bad_req = [req for req in download if isinstance(req, tuple)]
            #print(bad_req)
            # запросить снова ссылки для скачивания
            urls = await self.mediator.get_songs_urls (int_songs_redownloaded=len(bad_req))
            if bad_req:
                for i in bad_req:
                    urls.append(i)

    async def download_files(self, url, song_name, second_url, real_url, tries=0):
        print (f'Downloading {song_name}. Attempt - {tries}')
        async with aiohttp.ClientSession () as session:
            async with session.get (url, headers=headers) as res:
                bytes_len = res.content_length  # если 0 байтов то надо по новой все запрашивать
                print (f'Bytes: {bytes_len}', song_name)
                if bytes_len > 5000000:
                    if (tries > 1) or (second_url == real_url):
                        print(f'Unable to download {song_name} file is too big, tries exceeded')
                        return None # add one more try to find music
                    print (f'Unable to download {song_name} file is too big, trying another link')
                    tries += 1
                    return second_url, song_name, second_url, tries
                if bytes_len == 0:
                    if tries == 0:
                        tries += 1
                        return real_url, song_name, second_url, tries
                    elif tries == 1:
                        tries += 1
                        return second_url, song_name, second_url, tries
                    return None
                async with aiofiles.open (Path (Path (__file__).parents[1], 'music', song_name), 'wb') as f:
                    byte = 0
                    try:
                        async for chunk in res.content.iter_chunked (10240):
                            await asyncio.sleep (0)
                            await f.write (chunk)
                            byte += 10240
                            if byte % 102400 == 0:
                                print (f'Downloaded {byte}/{bytes_len} - {song_name}')
                    except Exception as err:
                        print (err)
                        if tries == 0:
                            tries += 1
                            return real_url, song_name, second_url, tries
                        elif tries == 1:
                            tries += 1
                            return second_url, song_name, second_url, tries
                        return None
        return None


async def download_music(url, batch: int=8):
    ls = Apple_songs (url).get_songs()
    mediator = Mediator(ls, batch)
    await Download(mediator).request()

async def main(urls):
    await asyncio.gather(*[download_music(url)for url in urls])


if __name__ == '__main__':
    link1 = 'https://music.apple.com/ru/album/eye-of-the-tiger/456794422?l=en-GB'
    start = time.time()
    asyncio.run(main([link1])) # 354
    print(time.time()-start)



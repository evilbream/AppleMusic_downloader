import asyncio

from downloader.decipher_links import main

async def start():
    link = input('Enter link(s) to the Apple Music playlist(s): ')
    link = link.split(',') if ',' in link else [link]
    link = [lin.rstrip(' ').lstrip('') for lin in link]
    await main(link)

asyncio.run(start())
# downloading awailable from one link or multiple
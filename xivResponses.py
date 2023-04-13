import asyncio
import logging

import discord
import aiohttp
import pyxivapi
from pyxivapi.models import Filter, Sort

import responses

client = pyxivapi.XIVAPIClient(api_key=responses.open_file('key_xivapi.txt'))


async def fetch_character(forename, surname, world):
    url = f'https://xiv-character-cards.drakon.cloud/characters/name/{world}/{forename} {surname}.png'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                if response.headers['Content-Type'] == 'image/png':
                    data = await response.read()
                    if data:
                        return data
            return None


async def fetch_lore(query):
    response = await client.lore_search(
        query=query,
        language='en'
    )
    await client.session.close()
    print(response)
    return response

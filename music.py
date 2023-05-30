import os
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import wavelink
import bot


async def on_node():
    node: wavelink.Node = wavelink.Node(uri='http://localhost:2333', password='actualmoron72075')
    await wavelink.NodePool.connect(client=bot.client, nodes=[node])
    wavelink.Player.autoplay = True

import asyncio
import io
import os
from dotenv import load_dotenv
import youtube_dl

import discord
from discord.ext import commands, tasks

import responses
import xivResponses

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)


async def send_message(message, user_message, is_private):
    return


def run_discord_bot():
    token = responses.open_file('key_discord.txt')

    @client.event
    async def on_ready():
        print(f'{client.user} is now running')
        activity = discord.Activity(name='with your feelings', type=discord.ActivityType.playing)
        await client.change_presence(activity=activity, status=discord.Status.online)
        try:
            synced = await client.tree.sync()
            print(f'Synced {len(synced)} commands')
        except Exception as e:
            print(f'Failed to sync commands: {e}')

    @client.tree.command(name='xivlodestone', description='Searches for a character on the Final Fantasy XIV Lodestone')
    async def xivlodestone(ctx, forename: str, surname: str, world: str):
        await ctx.response.defer(ephemeral=False)
        await asyncio.sleep(10)
        file = await xivResponses.fetch_character(forename, surname, world)
        if file:
            image = discord.File(io.BytesIO(file), filename='character.png')
            await ctx.followup.send(file=image)
        else:
            await ctx.followup.send('I couldn\'t find a character by that name, sorry!')

    @client.tree.command(name='xivlore', description='Search ingame data for matches against a given query.')
    async def xivlore(ctx, *, query: str):
        await ctx.response.defer(ephemeral=False)
        await asyncio.sleep(10)
        response = await xivResponses.fetch_lore(query)
        embed = discord.Embed(title=f"Results for '{query}'", color=0x00ff00)
        for result in response["Results"]:
            context = result["Context"]
            source = result["Source"]
            text = result["Text"]
            embed.add_field(name=context, value=f"{source}: {text}", inline=False)
        try:
            await ctx.followup.send(embed=embed)
        except Exception as e:
            print(e)
            await ctx.followup.send('Your search is too broad... maybe try again with a more specific query?')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)

        if '@1072402868319047813' in user_message:
            print(f"{username} said: '{user_message}' in {channel}")
            await send_message(message, user_message, is_private=False)
        if isinstance(message.channel, discord.DMChannel):
            print(f"{username} said: '{user_message}' in DMs")
            await send_message(message, user_message, is_private=True)

    client.run(token)

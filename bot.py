import io
import json
import os
import random
import re
import sqlite3

import asyncio
import discord
import pvporcupine
import shortuuid
import wavelink
from discord.ext import commands
from dotenv import load_dotenv
from google.cloud import texttospeech

import music
import responses
import xivResponses

load_dotenv()
porcupin = pvporcupine.create(
    access_key=os.getenv('LEOPARD_TOKEN'),
    keyword_paths=['Hey-Aimee_en_windows_v2_2_0.ppn']
)
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)
tts_client = texttospeech.TextToSpeechClient()
database = sqlite3.connect('quotes.db')
cursor = database.cursor()
database.execute('CREATE TABLE IF NOT EXISTS susquotesdisabled (server_id TEXT)')
user = ""


async def send_message(message, user_message, is_private):
    return


async def vote_start(channel: discord.VoiceChannel, message_channel):
    total_reactions = 0
    bot_count = 0
    for member in channel.members:
        if member.bot:
            bot_count += 1
    num_of_members = len(channel.members) - bot_count
    print(f'Skip vote has started in {channel.name}, there are {num_of_members} members in the channel')
    vote_declare = await message_channel.send('Vote to skip the song by reacting with 👍. {} members are required to '
                                              'skip the song'.format(round(num_of_members / 2)))
    await vote_declare.add_reaction('👍')
    await asyncio.sleep(15)
    vote_declare = await message_channel.fetch_message(vote_declare.id)
    for reaction in vote_declare.reactions:
        if reaction.emoji == '👍':
            total_reactions += reaction.count
    votes = total_reactions - 1
    if num_of_members == 1 or votes >= round(num_of_members / 2):
        print(f'{votes} members voted to skip the song out of {num_of_members} members in the channel')
        return True
    else:
        return False


async def is_mod(member: discord.Member) -> bool:
    return member.guild_permissions.manage_messages


def remove_word(string, word):
    # Check if the word is present in string
    if word in string:
        # To cover the case if the word is at the beginning
        # of the string or anywhere in the middle
        temp_word = word + " "
        string = string.replace(temp_word, "")

        # To cover the edge case if the word is at the end
        # of the string
        temp_word = " " + word
        string = string.replace(temp_word, "")

    # Return the resultant string
    return string


def run_discord_bot():
    token = os.getenv('DISCORD_TOKEN')
    porcupine = None
    pa = None
    audio_stream = None

    @client.event
    async def on_ready():
        print(f'{client.user} is now running')
        activity = discord.Activity(name='with your feelings', type=discord.ActivityType.playing)
        client.loop.create_task(music.on_node())
        responses.bot_user_ID = client.user.id
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

    @client.tree.command(name='quote', description='Adds a quote to the database')
    async def quote(ctx, *, message_id: str):
        await ctx.response.defer(ephemeral=False)
        message = await ctx.channel.fetch_message(message_id)
        unique_id = str(shortuuid.uuid())
        cursor.execute('INSERT INTO quotes VALUES (?, ?, ?, ?)',
                       (str(message.content), str(message.author), ctx.guild.id, unique_id))
        database.commit()
        await ctx.followup.send('Quote added to the database!')

    @client.tree.command(name='getquote', description='Gets a random quote from the database')
    async def getquote(ctx):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM quotes WHERE server_id = ?', (ctx.guild.id,))
        quotes = cursor.fetchall()
        if len(quotes) == 0:
            await ctx.followup.send('There are no quotes in the database for this server!')
        else:
            selected_quote = random.choice(quotes)
            await ctx.followup.send(f'"{selected_quote[0]}" - {selected_quote[1]}')

    @client.tree.command(name='getquotebyid', description='Gets a quote from the database by its ID')
    async def getquotebyid(ctx, quote_id: str):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM quotes WHERE unique_id = ? AND server_id = ?', (quote_id, ctx.guild.id))
        selected_quote = cursor.fetchone()
        if selected_quote:
            await ctx.followup.send(f'"{selected_quote[0]}" - {selected_quote[1]}')
        else:
            await ctx.followup.send('That quote doesn\'t exist!')

    @client.tree.command(name='listquotes', description='Lists in an embed all quotes in the database in this server')
    async def listquotes(ctx):
        await ctx.response.defer(ephemeral=False)
        cursor.execute('SELECT * FROM quotes WHERE server_id = ?', (ctx.guild.id,))
        quotes = cursor.fetchall()
        if len(quotes) == 0:
            await ctx.followup.send('There are no quotes in the database for this server!')
        else:
            embed = discord.Embed(title=f'Quotes for {ctx.guild.name}', color=0x00ff00)
            for target_quote in quotes:
                embed.add_field(name=target_quote[1], value=f'"{target_quote[0]}" \n ID: {target_quote[3]}',
                                inline=False)
            await ctx.followup.send(embed=embed)

    @client.tree.command(name='deletequote', description='Deletes a quote from the database by its ID (Moderator only)')
    async def deletequote(ctx, quote_id: str):
        await ctx.response.defer(ephemeral=False)
        if await is_mod(member=ctx.user):
            cursor.execute('SELECT * FROM quotes WHERE unique_id = ? AND server_id = ?', (quote_id, ctx.guild.id))
            selected_quote = cursor.fetchone()
            if selected_quote:
                cursor.execute('DELETE FROM quotes WHERE unique_id = ? AND server_id = ?', (quote_id, ctx.guild.id))
                database.commit()
                await ctx.followup.send('Quote deleted!')
            else:
                await ctx.followup.send('That quote doesn\'t exist!')
        else:
            await ctx.followup.send('Only moderators can use this command!')

    @client.tree.command(name='play', description='Plays a song from YouTube')
    async def play(ctx, *, search: str):
        await ctx.response.defer(ephemeral=False)
        try:
            query = await wavelink.YouTubeTrack.search(search, return_first=True)
        except wavelink.WavelinkException as e:
            return await ctx.followup.send('Invalid search query: {}'.format(e))
        destination = ctx.user.voice.channel
        if not ctx.guild.voice_client:
            vc: wavelink.Player = await destination.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.guild.voice_client
        if vc.is_playing():
            await vc.queue.put_wait(query)
            await ctx.followup.send(f'I added {query.title} to the queue!')
        else:
            await vc.play(query)
            await ctx.followup.send(f'Now playing: {vc.current.title}')

    @client.tree.command(name='join', description='join the voice channel you are in')
    async def join(ctx):
        await ctx.response.defer(ephemeral=False)
        guild = client.get_guild(ctx.guild.id)
        bot_member = guild.get_member(client.user.id)
        if not ctx.user.voice:
            return await ctx.followup.send(f'You aren\'t connected to a voice channel {ctx.user.mention}!')
        elif bot_member.voice and bot_member.voice.channel != ctx.user.voice.channel:
            await ctx.guild.voice_client.move_to(ctx.user.voice.channel)
            await ctx.followup.send(f'Moved to {ctx.user.voice.channel}')
        elif bot_member.voice and bot_member.voice.channel == ctx.user.voice.channel:
            await ctx.followup.send(f'I\'m already in {ctx.user.voice.channel} {ctx.user.mention}!')
        else:
            channel = ctx.user.voice.channel
            await channel.connect()
            await ctx.followup.send(f'Joined {channel}!')

    @client.tree.command(name='skip', description='Calls a vote to skip the current song')
    async def skip(ctx):
        await ctx.response.defer(ephemeral=False)
        message_channel = ctx.channel
        vc: wavelink.Player = ctx.guild.voice_client
        if vc is None:
            await ctx.followup.send('I\'m not playing any music right now!')
        elif not vc.is_playing or not vc.is_paused:
            await ctx.followup.send('I\'m not playing any music right now!')

        if await vote_start(ctx.user.voice.channel, message_channel):
            await ctx.followup.send(f'Skipping {vc.current.title}!')
            await vc.stop()
        else:
            await ctx.followup.send('The skip vote failed.')

    @client.tree.command(name='pause', description='Pauses the current song')
    async def pause(ctx):
        await ctx.response.defer(ephemeral=False)
        vc: wavelink.Player = ctx.guild.voice_client
        if vc is None:
            await ctx.followup.send('I\'m not playing any music right now!')
        elif vc.is_playing:
            await vc.pause()
            await ctx.followup.send('Paused the current song!')
        else:
            await ctx.followup.send('I\'m not playing any music right now!')

    @client.tree.command(name='resume', description='Resumes the current song')
    async def resume(ctx):
        await ctx.response.defer(ephemeral=False)
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and vc.is_paused:
            await vc.resume()
            await ctx.followup.send('Resumed the current song!')
        else:
            await ctx.followup.send('I\'m not playing any music right now!')

    @client.tree.command(name='disconnect', description='Disconnects the bot from the voice channel')
    async def disconnect(ctx):
        await ctx.response.defer(ephemeral=False)
        vc: wavelink.Player = ctx.guild.voice_client
        await vc.disconnect()
        await ctx.followup.send('I left the voice channel!')

    @client.tree.command(name='queue', description='Shows the current queue')
    async def queue(ctx):
        await ctx.response.defer(ephemeral=False)
        vc: wavelink.Player = ctx.guild.voice_client
        if vc is None:
            await ctx.followup.send('I\'m not playing any music right now!')
        elif vc.queue.is_empty:
            await ctx.followup.send('The queue is empty!')
        else:
            embed = discord.Embed(title='Queue', color=0x00ff00)
            for i, track in enumerate(vc.queue):
                embed.add_field(name=f'{i + 1}. {track.title}', value=f'Duration: {track.duration}', inline=False)
            await ctx.followup.send(embed=embed)

    @client.tree.command(name='susquotes', description='Enables or disables sus quotes. Enter enable or disable as the '
                                                       'status. (Moderator only)')
    async def susquotes(ctx, *, status: str):
        await ctx.response.defer(ephemeral=False)
        target_server = ctx.guild.id
        cursor.execute('SELECT * FROM susquotesdisabled WHERE server_id = ?', (target_server,))
        status_input = status.lower()
        if await is_mod(member=ctx.user):
            if status_input == 'disable':
                if cursor.fetchone():
                    await ctx.followup.send('Sus quotes are already disabled!')
                else:
                    cursor.execute('INSERT INTO susquotesdisabled VALUES (?)', (target_server,))
                    database.commit()
                    await ctx.followup.send('Sus quotes disabled!')
            elif status_input == 'enable':
                if cursor.fetchone() is None:
                    await ctx.followup.send('Sus quotes are already enabled!')
                else:
                    cursor.execute('DELETE FROM susquotesdisabled WHERE server_id = ?', (target_server,))
                    database.commit()
                    await ctx.followup.send('Sus quotes enabled!')

        else:
            await ctx.followup.send('Invalid answer, answer with simply enable or disable')

    @client.tree.command(name='speaktext', description='Converts text to speech')
    async def speaktext(ctx, *, text: str):
        await ctx.response.defer(ephemeral=False)
        channel = ctx.user.voice.channel
        guild = client.get_guild(ctx.guild.id)
        bot_member = guild.get_member(client.user.id)
        voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
        if not ctx.user.voice:
            await ctx.followup.send('You\'re not in a voice channel!')
            return
        elif voice_client and voice_client.is_connected():
            await voice_client.move_to(channel)
            if voice_client.is_playing():
                await ctx.followup.send('Already speaking or playing music! Try again later.')
                return
            tts_response = responses.generate_speech(text)
            with open('tts_response.mp3', 'wb') as f:
                f.write(tts_response)

            voice_client.play(discord.FFmpegPCMAudio('tts_response.mp3'), after=lambda e: os.remove('tts_response.mp3'))
            await ctx.followup.send(str(ctx.user) + ': ' + text)
        else:
            voice_client = await channel.connect()
            tts_response = responses.generate_speech(text)
            with open('tts_response.mp3', 'wb') as f:
                f.write(tts_response)

            voice_client.play(discord.FFmpegPCMAudio('tts_response.mp3'), after=lambda e: os.remove('tts_response.mp3'))
            await ctx.followup.send(str(ctx.user) + ': ' + text)

    @client.tree.command(name='allcommands', description='Shows a list of commands')
    async def allcommands(ctx):
        await ctx.response.defer(ephemeral=False)
        embed = discord.Embed(title='Commands', color=0x00ff00)
        for command in client.tree.get_commands():
            embed.add_field(name=command.name, value=command.description, inline=False)
        await ctx.followup.send(embed=embed)

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = message.author.display_name
        user_message = str(message.content)
        channel = str(message.channel)
        if 'sus' in user_message and message.guild is not None:
            server = message.guild.id
            cursor.execute('SELECT * FROM susquotesdisabled WHERE server_id = ?', (server,))
            if cursor.fetchone() is None:
                with open('amongus.json', 'r') as f:
                    quote = json.load(f)
                    random_quote = random.choice(quote)
                await message.channel.send(random_quote)

        if isinstance(message.channel, discord.DMChannel):
            print(f"{username} said: '{user_message}' in DMs")
            async with message.channel.typing():
                cleaned_message = remove_word(user_message, '<@1072402868319047813>')
                cleaned_username = re.sub(r'[^a-zA-Z0-9]+', '', username)
                print(f'Cleaned user: {cleaned_username}')
                response = responses.response_and_index(cleaned_message, cleaned_username)
                await message.channel.send(response)
                print(f'Responded in {message.channel} with {response}')
                return
        else:
            if '<@1072402868319047813>' in user_message:
                print(f"{username} said: '{user_message}' in {channel}")
                async with message.channel.typing():
                    cleaned_message = remove_word(user_message, '<@1072402868319047813>')
                    cleaned_username = re.sub(r'[^a-zA-Z0-9]+', '', username)
                    print(f'Cleaned user: {cleaned_username}')
                    response = responses.response_and_index(cleaned_message, cleaned_username)
                    await message.channel.send(response)
                    print(f'Responded in {message.channel} in {message.guild} with {response}')
                    return

    @client.event
    async def on_voice_state_update(member, before, after):
        nonlocal porcupine, pa, audio_stream
        if member != client.user:
            if after.channel is None:
                vc: wavelink.Player = member.guild.voice_client
                if vc is not None:
                    if len(vc.channel.members) == 1:
                        print(f'No one left in {before.channel} in {member.guild}, disconnecting in 60 seconds...')
                        await asyncio.sleep(60)
                        if len(vc.channel.members) == 1:
                            print(f'Disconnected from {before.channel} in {member.guild}.')
                            await vc.disconnect()
                        else:
                            print(f'Someone joined {before.channel} in {member.guild}, not disconnecting.')

    client.run(token)

import discord
import responses

intents = discord.Intents.default()
intents.message_content = True


async def send_message(message, user_message, is_private):
    try:
        response = responses.response_and_index(user_message, str(message.author))
        if is_private:
            await message.author.send(response)
        else:
            await message.channel.send(response)
    except Exception as e:
        print(e)


def run_discord_bot():
    token = responses.open_file('key_discord.txt')
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'{client.user} is now running')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)

        print(f"{username} said: '{user_message}' in {channel}")
        if '@1072402868319047813' in user_message:
            await send_message(message, user_message, is_private=False)
        if isinstance(message.channel, discord.DMChannel):
            await send_message(message, user_message, is_private=True)

    client.run(token)

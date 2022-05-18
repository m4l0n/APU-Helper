from discord.ext import commands
import discord
import platform
import os
import aiohttp
import asyncio
from datetime import datetime
import re
import moodle


TOKEN = "OTcyNDc3MDAyMzQwNzY5ODUy.YnZnyQ.LzpHXp7iY23o0pj06MpSYfyqyI0"
PREFIX = "-"
client = commands.Bot(command_prefix = PREFIX)


# @client.command(name = "test")
# async def main(ctx):
#     async with session.get('http://python.org') as response:
#         await ctx.send("Content-type:" + response.headers['content-type'])
#
#         html = await response.text()
#         await asyncio.sleep(10)
#         await ctx.send("Body:" + html[:15] + "...")
#
#
# @client.command(name = "test2")
# async def test2(ctx):
#     await ctx.send("Bruh")

async def create_embed(author: discord.Message.author, title, colour, fields, footer = None, image= None):
    embed = discord.Embed(title = title, colour = colour)
    embed.set_author(name = author.display_name, icon_url = author.avatar_url)
    for field in fields:
        embed.add_field(name = field[0], value = field[1], inline = field[2])
    if footer:
        embed.set_footer(text = footer)
    if image:
        embed.set_image(url = image)
    return embed


@client.command(name = "test")
async def get_events(ctx):
    embed_fields = [("Status", "Submitting to Moodle...", False)]
    embed = await create_embed(ctx.author, "Plagiarism Check", 0x569ff0, embed_fields, image="https://imgur.com/8IxwMOP.gif")
    # embed = discord.Embed(title = "Plagiarism Check", color = 0x569ff0)
    # embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
    # embed.add_field(name = "Status", value = "Submitting to Moodle...", inline = False)
    # embed.set_image(url = "https://imgur.com/8IxwMOP.gif")
    await ctx.send(embed = embed)


@client.command(name = "p_check")
async def check_plagiarism(ctx, link):
    url_re = re.compile(r'https://cdn.discordapp.com/attachments/[0-9]*/[0-9]*/[-a-zA-Z0-9@:%._\\+~#=]{1,256}')
    if (not url_re.match(link)):
        ctx.send("Url format invalid!")
        return
    file_name = re.search(r'https://cdn.discordapp.com/attachments/[0-9]*/[0-9]*/(.*?)$', link).group(1)
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            file_bytes = await response.read()
    embed = discord.Embed(title = "Plagiarism Check", color = 0x569ff0)
    embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
    embed.add_field(name = "Status", value = "Submitting to Moodle...", inline = False)
    embed.set_image(url = "https://imgur.com/8IxwMOP.gif")
    message_id = await ctx.send(embed = embed)
    async with ctx.channel.typing():
        plagiarism = await moodle_session.check_plagiarism(file_bytes, file_name)
    if (plagiarism):
        new_embed = discord.Embed(title = "Plagiarism Check", color = 0x569ff0)
        new_embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
        new_embed.add_field(name = "Status", value = "Done!", inline = True)
        new_embed.add_field(name = "Similarity", value = plagiarism, inline = True)
        await ctx.send(f'<@744367538615353344>')
        await message_id.edit(embed = new_embed)


@client.event
async def on_ready():
    # global moodle_session
    # credentials = {
    #     'username': 'TP062253',
    #     'password': '2TRY!vK6JTCF'
    # }
    # moodle_session = moodle.Moodle()
    # await moodle_session.login(credentials)
    guild = client.get_guild(870189007911399494)
    print("-------------------")
    print(f'Logged in as {client.user}')
    print(f"Python version: {platform.python_version()}")
    print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    print(f'Current Guild: {guild.name}')
    print("-------------------")


moodle_session = None
client.run(TOKEN)
#
# import discord
# from discord import app_commands
#
# import traceback
#
# # The guild in which this slash command will be registered.
# # It is recommended to have a test guild to separate from your "production" bot
# TEST_GUILD = discord.Object(0)
#
#
# class MyClient(discord.Client):
#     def __init__(self) -> None:
#         # Just default intents and a `discord.Client` instance
#         # We don't need a `commands.Bot` instance because we are not
#         # creating text-based commands.
#         intents = discord.Intents.default()
#         super().__init__(intents=intents)
#
#         # We need an `discord.app_commands.CommandTree` instance
#         # to register application commands (slash commands in this case)
#         self.tree = app_commands.CommandTree(self)
#
#     async def on_ready(self):
#         print(f'Logged in as {self.user} (ID: {self.user.id})')
#         print('------')
#
#     async def setup_hook(self) -> None:
#         # Sync the application command with Discord.
#         await self.tree.sync(guild=TEST_GUILD)
#
#
# class Feedback(discord.ui.Modal, title='Feedback'):
#     # Our modal classes MUST subclass `discord.ui.Modal`,
#     # but the title can be whatever you want.
#
#     # This will be a short input, where the user can enter their name
#     # It will also have a placeholder, as denoted by the `placeholder` kwarg.
#     # By default, it is required and is a short-style input which is exactly
#     # what we want.
#     name = discord.ui.TextInput(
#         label='Name',
#         placeholder='Your name here...',
#     )
#
#     # This is a longer, paragraph style input, where user can submit feedback
#     # Unlike the name, it is not required. If filled out, however, it will
#     # only accept a maximum of 300 characters, as denoted by the
#     # `max_length=300` kwarg.
#     feedback = discord.ui.TextInput(
#         label='What do you think of this new feature?',
#         style=discord.TextStyle.long,
#         placeholder='Type your feedback here...',
#         required=False,
#         max_length=300,
#     )
#
#     async def on_submit(self, interaction: discord.Interaction):
#         await interaction.response.send_message(f'Thanks for your feedback, {self.name.value}!', ephemeral=True)
#
#     async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
#         await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)
#
#         # Make sure we know what the error actually is
#         traceback.print_tb(error.__traceback__)
#
#
# client = MyClient()
#
#
# @client.tree.command(guild=TEST_GUILD, description="Submit feedback")
# async def feedback(interaction: discord.Interaction):
#     # Send the modal with an instance of our `Feedback` class
#     # Since modals require an interaction, they cannot be done as a response to a text command.
#     # They can only be done as a response to either an application command or a button press.
#     await interaction.response.send_modal(Feedback())
#
#
# client.run('OTcyNDc3MDAyMzQwNzY5ODUy.YnZnyQ.LzpHXp7iY23o0pj06MpSYfyqyI0')
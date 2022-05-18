import asyncio
import aiohttp
import aiohttp.web
import os
import sys
import discord
import json
import time
import platform
import arrow
import re
import o365
import moodle
import apspace
from bs4 import BeautifulSoup
from datetime import datetime
from discord.ext import commands, tasks
import discord.utils
import logging
from scihub import SciHub
from ics import Calendar
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord_logging.handler import DiscordHandler
from custom_logger import DebugStreamHandler, DebugDiscordHandler

"""
OS Environment Variables
    int:Discord Bot Token
    str:Intended Prefix for the Bot
    str:APSpace Username
    str:APSpace Password
    str:APSpace API KEY
    int:Discord User ID
    str:Discord Webhook URL for Logs
"""
TOKEN = os.environ['TOKEN']
USERNAME = os.environ['USERNAME']
PWD = os.environ['PASSWORD']
USER_ID = os.environ['USER_ID']
WEBHOOK_URL = os.environ['WEBHOOK_URL']

PREFIX = "!"
client = commands.Bot(command_prefix = PREFIX)  # Initialise Discord Bot


async def create_embed(title, colour, fields, footer=None, image=None, author: discord.Message.author = None):
    embed = discord.Embed(title = title, colour = colour)
    if author:
        embed.set_author(name = author.display_name, icon_url = author.avatar_url)
    for field in fields:
        embed.add_field(name = field[0], value = field[1], inline = field[2])
    if footer:
        embed.set_footer(text = footer)
    if image:
        embed.set_image(url = image)
    return embed


@client.command(name = "otp")
async def take_attendance(ctx, otp):
    """
    Sends attendance status in Embed depending on the value returned by sign_otp() function.

    Raises OTPError exception if:
      Format is invalid (length of otp < 3) OR
      OTP is incorrect

    Parameters
    ----------
    ctx : Context
    otp : str
    """
    try:
        class_code = await apspace_session.take_attendance(otp)
        average_attendance = await apspace_session.get_attendance_percentage()
        embed_fields = [("Success", "Attendance taken successfully", False),
                        ("Class Code", class_code, False),
                        ("Overall Attendance", average_attendance, True),
                        "Timestamp", arrow.now('Asia/Kuala_Lumpur').format('DD/MM/YYYY hh:mm A'), True]
        embed = await create_embed(ctx.author, "Sign Attendance", colour = 0x26ff00, fields = embed_fields)
        await ctx.send(embed = embed)
    except apspace.OTPError as e:
        embed_fields = [("Error", "Error Message: " + str(e), False),
                        ("Timestamp", arrow.now('Asia/Kuala_Lumpur').format('DD/MM/YYYY hh:mm A'), False)]
        embed = await create_embed(ctx.author, "Sign Attendance", colour = 0xaf1e2d, fields = embed_fields)
        await ctx.send(embed = embed)


@client.command(name = "doi")
async def get_pdf(ctx, doi):
    """
    Gets PDF from SciHub.check_doi_format() and uploads to channel.

    Parameters
    ----------
    ctx : Context
    doi : str
    """
    scihub = SciHub(doi)
    if not scihub.check_doi_format():
        await ctx.send("DOI Number is Invalid!")
    else:
        pdf, fname = scihub.search_sci_hub()
        file = discord.File(pdf, filename = fname)
        await ctx.send(file = file)


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
    embed_fields = [("File Name", file_name, False), ("Status", "Submitting to Moodle...", False)]
    embed = await create_embed(author = ctx.author, title = "Plagiarism Check", colour = 0x569ff0,
                               fields = embed_fields, image = "https://imgur.com/8IxwMOP.gif")
    message_id = await ctx.send(embed = embed)
    async with ctx.channel.typing():
        plagiarism = await moodle_session.check_plagiarism(file_bytes, file_name)
    if (plagiarism):
        embed_fields = [("File Name", file_name, False), ("Status", "Done", True), ("Similarity", plagiarism, True)]
        new_embed = await create_embed(author = ctx.author, title = "Plagiarism Check", colour = 0x569ff0,
                                       fields = embed_fields)
        await ctx.send(f'<@{USER_ID}>')
        await message_id.edit(embed = new_embed)


@client.command(name = 'purge')
async def purge_messages(ctx, limit: int):
    deleted = await ctx.channel.purge(limit = limit)
    await ctx.channel.send(f'Deleted {len(deleted)} message(s)!', delete_after = 5)


async def schedule_timetable():
    """
    Gets list of schedules from apspace.get_weekly_timetable()
    Create schedule (Scheduler) that calls class_reminders() from every event
    """
    try:
        print('scheduling timetables...')
        async for schedule in apspace_session.get_weekly_timetable():
            module_name = schedule['MODULE_NAME']
            day_name = f'{schedule["DAY"].title()}day'
            time_start = schedule['TIME_FROM']
            duration = arrow.get(schedule['TIME_FROM_ISO']).humanize(
                arrow.get(schedule['TIME_TO_ISO']), only_distance = True
            )
            scheduler.add_job(class_reminders, "date", run_date=schedule['TIME_FROM_ISO'],
                              args = (module_name, day_name, time_start, duration))
    except Exception as e:
        print(str(e))
        sys.exit(1)


async def initialise_o365():
    try:
        scopes = [
            "Calendars.Read",
            "Calendars.Read.Shared",
            "Channel.ReadBasic.All",
            "IMAP.AccessAsUser.All",
            "openid profile",
            "Team.ReadBasic.All",
            "User.Read email"
        ]
        o365_session = o365.Account(scopes = scopes)
        await o365_session.login()
        return o365_session
    except ValueError:
        sys.exit(1)
    except (o365.TokenExpiredError, o365.TokenInvalidError) as te:
        global O365
        O365 = await initialise_o365()


async def initialise_moodle():
    try:
        credentials = {
            'username': USERNAME,
            'password': PWD
        }
        moodle_session = moodle.Moodle()
        await moodle_session.login(credentials)
        return moodle_session
    except moodle.CredentialsInvalid:
        sys.exit(1)


async def initialise_apspace():
    try:
        credentials = {
            'username': USERNAME,
            'password': PWD
        }
        apspace_session = apspace.APSpace()
        await apspace_session.login(credentials)
        return apspace_session
    except apspace.CredentialsInvalid:
        sys.exit(1)


async def class_reminders(module_name, day_name, time_start, duration):
    """
    Tags user and sends a reminder in the form of Embed.

    Parameters
    ----------
    module_name : str
    day_name : str
    time_start: str
    duration: str
    """
    try:
        meeting_link = await O365.two_hour_schedule()
        channel = client.get_channel(870189007911399497)
        embed_fields = [("Class Name", module_name, False), ("Time", f'{day_name.title()}, {time_start}', True),
                        ("Duration", duration, True), ("Meeting Link", meeting_link, False)]
        embed = await create_embed(author = ctx.author, title = "Class Reminder", colour = 0x1ed760,
                                   fields = embed_fields)

        await channel.send(f'<@{USER_ID}>')
        await channel.send(embed = embed)
    except o365.TokenInvalidError as e:
        sys.exit(1)


async def assignment_reminders():
    try:
        channel = client.get_channel(971291316866666506)
        for event in await moodle_session.get_events():
            # event_end_date = datetime.fromtimestamp(event['timestart']).strftime("%c")
            soup = BeautifulSoup(event['formattedtime'], "lxml")
            event_end_date = f'{soup.find("a").contents[0]}  {arrow.now("Asia/Kuala_Lumpur").year}'
            embed_fields = [("Assignment", event['name'], False),
                            ("Course Name", event['course']['fullnamedisplay'], False),
                            ("Submission Link", event['url'], False), ("Deadline", event_end_date,  False)]
            embed = await create_embed(title = "Assignment Reminder", colour = 0x1ed760, fields = embed_fields)
            await channel.send(embed = embed)
    except aiohttp.web.HTTPError:
        sys.exit(1)
    except o365.TokenExpiredError as e:
        print(str(e))


@tasks.loop(hours = 24)
async def show_semester_details():
    print("Updating semester details...")
    try:
        current_semester, cgpa = await apspace_session.get_semester_details()
        intake, course_name, course_type = await apspace_session.get_intake_details("all_current")
        attendance_percentage = await apspace_session.get_attendance_percentage()
        semester_intake_details = {'Course Name': course_name,
                                   'Intake': intake,
                                   'Course Type': course_type,
                                   'Semester': current_semester,
                                   'CGPA': cgpa,
                                   'Attendance': attendance_percentage}
        category = discord.utils.get(guild.categories, name = "📊 STATS 📊")

        if category:
            for channel in category.channels:
                await channel.delete()
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False)
            }
            category = await guild.create_category(name = "📊 STATS 📊", position=0, overwrites=overwrites)

        for key in semester_intake_details.keys():
            await category.create_voice_channel(name = f'{key}: {semester_intake_details[key]}')
    except Exception as e:
        print(e)


@show_semester_details.before_loop
async def before_show_semester():
    for _ in range(60 * 60 * 24):
        if arrow.now('Asia/Kuala_Lumpur').hour == 12 + 12:
            return
        await asyncio.sleep(1)


async def scheduler_logs():
    """
    Sends a log for all jobs in scheduler.
    """
    channel = client.get_channel(966521544442544180)
    await channel.purge()
    i = 1
    for job in scheduler.get_jobs():
        log = f'INFO : schedule : Job {job.id} Running On {job.next_run_time.strftime("%A, %m/%d/%Y, %I:%M %p")}'
        await channel.send(log)
        i += 1


def initialise_loggers():
    o365_logger = logging.getLogger('o365')
    apscheduler_logger = logging.getLogger('apscheduler.scheduler')
    moodle_logger = logging.getLogger('moodle')
    apspace_logger = logging.getLogger('apspace')

    formatter = logging.Formatter('%(asctime)s : %(name)s : %(levelname)s : %(message)s',
                                  datefmt = '%m/%d/%Y %I:%M:%S %p')
    formatter.converter = lambda *args: arrow.now('Asia/Kuala_Lumpur').timetuple()
    stream_logger = logging.StreamHandler()
    stream_logger.setFormatter(formatter)
    discord_logger = DiscordHandler(
        service_name = "Logger",
        webhook_url = WEBHOOK_URL
    )
    discord_logger.setFormatter(formatter)
    custom_stream_logger = DebugStreamHandler()
    custom_stream_logger.setFormatter(formatter)
    custom_discord_logger = DebugDiscordHandler(
        service_name = "Logger",
        webhook_url = WEBHOOK_URL
    )
    custom_discord_logger.setFormatter(formatter)

    o365_logger.addHandler(stream_logger)
    moodle_logger.addHandler(stream_logger)
    apspace_logger.addHandler(stream_logger)
    apscheduler_logger.addHandler(custom_stream_logger)

    o365_logger.addHandler(discord_logger)
    # apscheduler_logger.addHandler(custom_discord_logger)
    moodle_logger.addHandler(discord_logger)
    apspace_logger.addHandler(discord_logger)

    apscheduler_logger.setLevel(level = logging.DEBUG)
    o365_logger.setLevel(level = logging.DEBUG)
    moodle_logger.setLevel(level = logging.INFO)
    apspace_logger.setLevel(level = logging.INFO)

    o365_logger.propagate = False
    apscheduler_logger.propagate = False
    moodle_logger.propagate = False
    apspace_logger.propagate = False


@client.event
async def on_ready():
    """

    Prints a ready message once the bot is initialised.
    """
    # await scheduler_logs()
    global guild, moodle_session, apspace_session, O365
    guild = client.get_guild(870189007911399494)
    O365 = await initialise_o365()
    moodle_session = await initialise_moodle()
    apspace_session = await initialise_apspace()
    await show_semester_details()
    await assignment_reminders()
    timetable_job.modify(next_run_time = arrow.now('Asia/Kuala_Lumpur'))
    scheduler.print_jobs()
    print("-------------------")
    print(f'Logged in as {client.user}')
    print(f"Python version: {platform.python_version()}")
    print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    print(f'Current Guild: {guild.name}')
    print("-------------------")
    end = time.perf_counter() - start
    print(f"Program finished in {end:0.2f} seconds.")


if __name__ == "__main__":
    guild = None
    start = time.perf_counter()
    initialise_loggers()
    O365 = None
    moodle_session = None
    apspace_session = None
    scheduler = AsyncIOScheduler(timezone = "Asia/Kuala_Lumpur")
    timetable_job = scheduler.add_job(schedule_timetable, "cron", day_of_week = "sun", timezone = "Asia/Kuala_Lumpur")
    scheduler.start()
    client.run(TOKEN)

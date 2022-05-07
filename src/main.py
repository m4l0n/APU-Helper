import asyncio
import os
import sys
import discord
import pytz
import requests
import json
import threading
import time
import platform
import o365
import moodle
import apspace
from bs4 import BeautifulSoup
from datetime import datetime
from pytz import timezone
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
"""
TOKEN = os.environ['TOKEN']
USERNAME = os.environ['USERNAME']
PWD = os.environ['PASSWORD']
API_KEY = os.environ['API_KEY']
USER_ID = os.environ['USER_ID']
WEBHOOK_URL = os.environ['WEBHOOK_URL']

PREFIX = "!"
# Initialise Discord Bot
client = commands.Bot(command_prefix = PREFIX)
days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']


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
        class_code = apspace.take_attendance(otp)
        average_attendance = apspace.get_attendance()
        embed = discord.Embed(title = "Sign Attendance", color = 0x569ff0)
        embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
        embed.add_field(name = "Success", value = "Attendance taken successfully", inline = False)
        embed.add_field(name = "Class Code", value = class_code, inline = False)
        embed.add_field(name = "Overall Attendance", value = average_attendance, inline = True)
        embed.add_field(name = "Timestamp", value = datetime.now(), inline = True)
        await ctx.send(embed = embed)
    except apspace.OTPError as e:
        embed = discord.Embed(title = "Sign Attendance", color = 0xaf1e2d)
        embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
        embed.add_field(name = "Error", value = "Error Message: " + str(e), inline = False)
        embed.add_field(name = "Timestamp", value = datetime.now())
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


@client.command(name = 'purge')
async def purge_messages(ctx, limit: int):
    deleted = await ctx.channel.purge(limit = limit)
    await ctx.channel.send(f'Deleted {len(deleted)} message(s)!', delete_after = 5)


def schedule_timetable():
    """
    Reads calendar.ics and parse the events details.
    Creates dictionary of every schedule and writes to file.
    Create schedule (Scheduler) that calls send_reminder() from every event

    Returns
    ----------
    scheduler : Scheduler object that contains a set of all schedules created
    """
    scheduler = AsyncIOScheduler(timezone = "Asia/Kuala_Lumpur")
    schedule_dict = {day: {} for day in days}
    try:
        with open('calendar.ics', 'r') as fileHandler:
            gcal = Calendar(fileHandler.read())
            for component in gcal.events:
                module_name = component.name
                dtstart = component.begin  # Arrow object
                dtend = component.end
                duration = dtstart.humanize(dtend, only_distance = True)  # Gets range between dtstart and dtend
                day_name = (dtstart.format('dddd', locale = 'en_GB')).lower()  # Gets day of the week from date
                schedule_dict[day_name][module_name] = [dtstart.time().strftime("%I:%M %p"),
                                                        dtend.time().strftime("%I:%M %p"), duration]
                exec(
                    f'scheduler.add_job(send_reminder, "cron", day_of_week="{day_name[0:3]}", hour={dtstart.strftime("%-H")}, minute={dtstart.strftime("%-M")}, timezone="Asia/Kuala_Lumpur",'
                    f'args=("{module_name}", "{day_name}", "{dtstart.strftime("%I:%M %p")}", "{duration}"))')
        with open('schedule.json', 'w', encoding = 'utf-8') as f:
            json.dump(schedule_dict, f, ensure_ascii = False, indent = 4)
        return scheduler
    except FileNotFoundError:
        print("Calendar.ics file not found! Can't parse timetable.")
        sys.exit(1)
    # Exceptions from ics.py
    except (ValueError, NotImplementedError) as ve:
        print(str(ve))
        sys.exit(1)


def initialise_o365():
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
        return o365.Account(scopes = scopes)
    except ValueError:
        sys.exit(1)
    except (o365.TokenExpiredError, o365.TokenInvalidError) as te:
        global O365
        O365 = initialise_o365()


def initialise_moodle():
    try:
        credentials = {
            'username': USERNAME,
            'password': PWD
        }
        return moodle.Moodle(credentials)
    except moodle.CredentialsInvalid:
        sys.exit(1)


def initialise_apspace():
    try:
        credentials = {'username': 'TP062253', 'password': '2TRY!vK6JTCF'}
        '''{
            'username': USERNAME,
            'password': PWD
        }'''
        return apspace.APSpace(credentials)
    except apspace.CredentialsInvalid:
        sys.exit(1)


async def send_reminder(module_name, day_name, time, duration):
    """
    Tags user and sends a reminder in the form of Embed.

    Parameters
    ----------
    module_name : str
    day_name : str
    time: str
    duration: str
    """
    try:
        meeting_link = O365.two_hour_schedule()
        channel = client.get_channel(870189007911399497)
        embed = discord.Embed(title = "Class Reminder", color = 0x1ed760)
        embed.set_author(name = client.user.display_name, icon_url = client.user.avatar_url)
        embed.add_field(name = "Class Name", value = module_name, inline = False)
        embed.add_field(name = "Time", value = f'{day_name.title()}, {time}', inline = True)
        embed.add_field(name = "Duration", value = duration, inline = True)
        embed.add_field(name = "Meeting link", value = meeting_link, inline = False)

        await channel.send(f'<@{USER_ID}>')
        await channel.send(embed = embed)
    except o365.TokenInvalidError as e:
        sys.exit(1)


async def assignment_reminders():
    try:
        channel = client.get_channel(971291316866666506)
        for event in moodle.get_events():
            # event_end_date = datetime.fromtimestamp(event['timestart']).strftime("%c")
            soup = BeautifulSoup(event['formattedtime'], "lxml")
            event_end_date = soup.find('a').contents[0]
            embed = discord.Embed(title = "Assignment Reminder", colour = 0x1ed760)
            embed.set_author(name = client.user.display_name, icon_url = client.user.avatar_url)
            embed.add_field(name = "Assignment", value = event['name'], inline = False)
            embed.add_field(name = "Course Name", value = event['course']['fullnamedisplay'], inline = False)
            embed.add_field(name = "Submission Link", value = event['url'], inline = False)
            embed.add_field(name = "Deadline", value = event_end_date, inline = False)
            await channel.send(embed = embed)
    except requests.HTTPError:
        sys.exit(1)


@tasks.loop(hours = 24)
async def show_semester_details():
    current_semester, cgpa = apspace.get_semester_details()
    intake, course_name, course_type = apspace.get_intake_details("all_current")
    attendance_percentage = apspace.get_attendance_percentage()
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


@show_semester_details.before_loop
async def before_show_semester():
    for _ in range(60 * 60 * 24):
        if dt.datetime.now().hour == 12 + 12:
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
    formatter.converter = lambda *args: datetime.now(tz=timezone('Asia/Kuala_Lumpur')).timetuple()
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
    apscheduler_logger.addHandler(custom_discord_logger)
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
    global guild
    guild = client.get_guild(870189007911399494)
    await show_semester_details()
    await assignment_reminders()
    print("-------------------")
    print(f'Logged in as {client.user}')
    print(f"Python version: {platform.python_version()}")
    print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    print(f'Current Guild: {guild.name}')
    print("-------------------")


if __name__ == "__main__":
    guild = None
    initialise_loggers()
    scheduler = schedule_timetable()
    scheduler.start()
    O365 = initialise_o365()
    moodle = initialise_moodle()
    apspace = initialise_apspace()
    client.run(TOKEN)

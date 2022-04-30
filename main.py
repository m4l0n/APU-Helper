import asyncio
import os
import discord
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
from discord.ext import commands
import threading
import time
from scihub import SciHub
from ics import Calendar
import platform
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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

PREFIX  = "!"
LOGS_CHANNEL = 0 # Channel ID where you want to send logs to : int
REMINDER_CHANNEL = 0 # Channel ID where you want the class reminders to be sent to : int
client = commands.Bot(command_prefix=PREFIX)
days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']


class OTPInvalid(commands.CommandError):
  """
  An exception class that inherits from discord.ext.commands.CommandError.

  Attributes
  ----------
  message : str
      Error message string.

  Methods
  -------
  __str__:
      Overwrites str() to return error message string.
  """
  def __init__(self, message, *args, **kwargs):
    self.message = message
    super().__init__(self.message)

  def __str__(self):
    """
    Overwrites str() to return error message string.

    Returns
    -------
    self.message : Error message string
    """
    return self.message


@client.command(name="otp")
async def take_attendance(ctx, otp):
  """
  Sends attendance status in Embed depending on the value returned by sign_otp() function.

  Raises OTPInvalid exception if:
    Format is invalid (length of otp < 3) OR
    OTP is incorrect

  Parameters
  ----------
  ctx : Context
  otp : str
  """
  try:
    if (len(otp) != 3):
      raise OTPInvalid("OTP Format Invalid!")
    else:
      attendance, status = sign_otp(int(otp))
      if (attendance == "N"):
        raise OTPInvalid(status)
      else:
        average_attendance = get_attendance()
        embed = discord.Embed(title = "Sign Attendance", color=0x569ff0)
        embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
        embed.add_field(name="Success", value="Attendance taken successfully", inline=False)
        embed.add_field(name="Class Code", value=status, inline=False)
        embed.add_field(name="Overall Attendance", value=average_attendance, inline=True)
        embed.add_field(name="Timestamp", value=datetime.now(), inline=True)
      await ctx.send(embed=embed)
  except OTPInvalid as e:
    embed = discord.Embed(title = "Sign Attendance", color=0xaf1e2d)
    embed.set_author(name = ctx.author.display_name, icon_url = ctx.author.avatar_url)
    embed.add_field(name="Error", value="Error Message: " + str(e), inline=False)
    embed.add_field(name="Timestamp", value=datetime.now())
    await ctx.send(embed=embed)


@client.command(name="doi")
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
    file = discord.File(pdf, filename=fname)
    await ctx.send(file=file)


@client.command(name='purge')
async def purge_messages(ctx, limit: int):
  deleted = await ctx.channel.purge(limit=limit)
  await ctx.channel.send(f'Deleted {len(deleted)} message(s)!', delete_after=5)


def sign_otp(otp):
  """
  Sends a POST request with the otp and returns the status.

  Parameters
  ----------
  otp : int
  """
  headers, ticket = get_service_ticket("attendix")
  payload = {
    "operationName": "updateAttendance",
    "variables": {
      "otp": f'{otp:03d}'
    },
    "query": "mutation updateAttendance($otp: String!) {updateAttendance(otp: $otp) {id   attendance    classcode    date    startTime    endTime    classType    __typename  }}"
  }

  headers.update({
    'ticket': ticket,
    'x-amz-user-agent': 'aws-amplify/2.0.7',
    'x-api-key': API_KEY
  })

  sign_otp = requests.post("https://attendix.apu.edu.my/graphql", json=payload, headers=headers).json()
  if(sign_otp['data'] == "null" or not sign_otp['data']):
    error_message = sign_otp['errors'][0]['message']
    attendance = "N"
    return attendance, error_message
  else:
    if(sign_otp['data']['updateAttendance']['attendance'] == "Y"):
      class_code = sign_otp['data']['updateAttendance']['classcode']
      attendance = "Y"
      return attendance, class_code


def get_attendance():
  """
  Gets header and ticket (API authentication) from get_service_ticket() function.

  Parse all attendance percentage from every module in second semester and counts average percentage.

  Parameters
  ----------
  otp : int

  Returns
  ----------
  total_attendance / count : Average attendance percentage of the semester
  """
  headers, ticket = get_service_ticket("student/attendance")

  attendance_url = f'https://api.apiit.edu.my/student/attendance?intake=APD2F2109SE&ticket={ticket}'
  response = requests.get(attendance_url, headers=headers).json()
  total_attendance, count = 0, 0
  for i in response:
    if (i['SEMESTER'] == 2):
      total_attendance += i['PERCENTAGE']
      count += 1
  return round(total_attendance / count, 2)


def get_service_ticket(service_name):
  """
  Gets ticket (API authentication) from API according to the service_name provided ("attendix OR student/attendance).

  Parameters
  ----------
  service_name : int

  Returns
  ----------
  headers : Request headers
  service_ticket : Authentication string to API
  """
  headers = {
    'sec-ch-ua': '"Not A;Brand\";v=\"99\", \"Chromium\";v=\"99\", \"Microsoft Edge\";v=\"99\"',
    'DNT': '1',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55',
    'sec-ch-ua-platform': '"Windows"',
    'Origin': 'https://apspace.apu.edu.my',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://apspace.apu.edu.my/',
    'Content-type': 'application/x-www-form-urlencoded'
  }

  payload = {
    'username': USERNAME,
    'password': PWD
  }

  ticket_url = requests.post('https://cas.apiit.edu.my/cas/v1/tickets', data=payload, headers=headers).text
  soup = BeautifulSoup(ticket_url, "lxml")
  ticket = soup.find("form").get('action').replace('https://cas.apiit.edu.my/cas/v1/tickets/', '')

  service_ticket_url = f'https://cas.apiit.edu.my/cas/v1/tickets/{ticket}?service=https://api.apiit.edu.my/{service_name}'

  service_ticket = requests.post(service_ticket_url, data="", headers=headers).text

  return headers, service_ticket


def schedule_timetable():
  """
  Reads calendar.ics and parse the events details.
  Creates dictionary of every schedule and writes to file.
  Create schedule (Scheduler) that calls send_reminder() from every event

  Returns
  ----------
  scheduler : Scheduler object that contains a set of all schedules created
  """
  scheduler = AsyncIOScheduler()
  schedule_dict = {day:{} for day in days}
  try:
    with open('calendar.ics', 'r') as fileHandler:
      gcal = Calendar(fileHandler.read())
      for component in gcal.events:
        module_name = component.name
        dtstart = component.begin # Arrow object
        dtend = component.end
        duration = dtstart.humanize(dtend, only_distance = True)  # Gets range between dtstart and dtend
        day_name = (dtstart.format('dddd', locale = 'en_GB')).lower()  # Gets day of the week from date
        schedule_dict[day_name][module_name] = [dtstart.time().strftime("%I:%M %p"), dtend.time().strftime("%I:%M %p"), duration]
        exec(f'scheduler.add_job(send_reminder, "cron", day_of_week="{day_name[0:3]}", hour={dtstart.strftime("%-H")}, minute={dtstart.strftime("%-M")}, timezone="Asia/Kuala_Lumpur",'
             f'args=("{module_name}", "{day_name}", "{dtstart.strftime("%I:%M %p")}", "{duration}"))')
    with open('schedule.json', 'w', encoding='utf-8') as f:
      json.dump(schedule_dict, f, ensure_ascii=False, indent=4)
    return scheduler
  except FileNotFoundError as e:
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
    account = o365.Account(scopes = scopes)
    return account
  except ValueError as ve:
    print(str(ve))
    sys.exit(1)
  except (o365.TokenExpiredError, o365.TokenInvalidError) as te:
    print(te.message)
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
    meeting_link = account.two_hour_schedule()
    channel = client.get_channel(870189007911399497)
    embed = discord.Embed(title="Class Reminder", color=0x1ed760)
    embed.set_author(name=client.user.display_name, icon_url=client.user.avatar_url)
    embed.add_field(name="Class Name", value=module_name, inline=False)
    embed.add_field(name="Time", value=f'{day_name.title()}, {time}', inline=True)
    embed.add_field(name="Duration", value=duration, inline=True)
    embed.add_field(name="Meeting link", value=meeting_link, inline = False)

    await channel.send(f'<@{USER_ID}>')
    await channel.send(embed=embed)
  except o365.TokenInvalidError as e:
    print(e.message)
    sys.exit(1)


async def scheduler_logs():
  """
  Sends a log for all jobs in scheduler.
  """
  channel = client.get_channel(LOGS_CHANNEL)
  await channel.purge()
  i = 1
  for job in scheduler.get_jobs():
    log = f'INFO : schedule : Job {job.id} Running On {job.next_run_time.strftime("%A, %m/%d/%Y, %I:%M %p")}'
    await channel.send(log)
    i += 1


@client.event
async def on_ready():
  """

  Prints a ready message once the bot is initialised.
  """
  await scheduler_logs()
  print(f'Logged in as {client.user}')
  print(f"Python version: {platform.python_version()}")
  print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
  print(f'Current Guild: {client.guilds[0].name}')
  print("-------------------")


if __name__ == "__main__":
    account = initialise_o365()
  scheduler = schedule_timetable()
  scheduler.start()
  client.run(TOKEN)

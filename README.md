# APU-Helper
A Discord-based bot to provide utilities for university purposes. (Asia Pacific University)

<br/>

## Installing requirements

### CLI

```pip install -r requirements.txt```

<br/>

## OS Environment Variables
  - int:Discord Bot Token
  - str:Intended Prefix for the Bot
  - str:APSpace Username
  - str:APSpace Password
  - str:APSpace API KEY
  - int:Discord User ID
  - str:Webhook URL for logging

```EXPORT $VAR = VALUE```

<br/>

## Additional Requirements

Download calendar.ics from APSpace Timetable to the same directory as `main.py`

<br/>

## Functions

### 1. Take Attendance

Example:
```!otp 123```

<br/> 

### 2. Class Reminders

Note:

See [Additional Requirements](#Additional-Requirements)

<br/>

### 3. Download Journal Articles for Free

Example:
```!doi 10.1145/3147.3165```

<br/>

### 4. Assignment Reminders

Automatically parse assignment events from Moodle and send reminders in the form of Embeds to your desired channel.

<br/>

## Misc

The bot will send logs to your desired channel for debugging purposes.

from logging import StreamHandler, DEBUG
from discord_logging.handler import DiscordHandler


class DebugStreamHandler(StreamHandler):
    def __init__(self):
        StreamHandler.__init__(self)

    def emit(self, record):
        if not record.levelno == DEBUG:
            return
        super().emit(record)


class DebugDiscordHandler(DiscordHandler):
    def __init__(self, service_name, webhook_url):
        DiscordHandler.__init__(self, service_name, webhook_url)

    def emit(self, record):
        if not record.levelno == DEBUG:
            return
        if record.message == "Looking for jobs to run":
            return
        super().emit(record)
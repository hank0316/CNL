import logging.config

from salmon import queue
from salmon.routing import Router
from salmon.server import LMTPReceiver, Relay

from . import settings
import json

logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'],
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = LMTPReceiver(settings.receiver_config['host'],
                                 settings.receiver_config['port'])

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD = True
Router.UNDELIVERABLE_QUEUE = queue.Queue("run/undeliverable")


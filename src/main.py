#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" WIP

Author: Preocts <preocts@preocts.com>
"""
import time
import logging

from src.loadenv import LoadEnv
from src.ircclient import IRCClient


def main() -> None:
    """ Main yo """
    secrets = LoadEnv()
    secrets.load()
    client = IRCClient(
        secrets.get("BOT_NAME"),
        secrets.get("BOT_OAUTH_TWITCH"),
        secrets.get("SERVER"),
        int(secrets.get("PORT")),
    )
    client.connect()
    time.sleep(5)
    client.join_channel("#travelcast_bot")
    while client.connected:
        while not client.read_queue_empty:
            message = client.read_next
            print(f"RAW OUT >>> {message.message}")
            print(f"TERM OUT >>> {message.content}")
            if message.command == "PING":
                print("PONG!")
                # client.send("PONG :" + message.split(":", 1)[1])
    client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()

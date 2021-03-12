#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" WIP

Author: Preocts <preocts@preocts.com>
"""
import time
import logging

from src.loadenv import LoadEnv
from src.ircconnect import IRCConnect


def main() -> None:
    """ Main yo """
    secrets = LoadEnv()
    secrets.load()
    client = IRCConnect(
        secrets.get("BOT_NAME"),
        secrets.get("BOT_OAUTH_TWITCH"),
        secrets.get("SERVER"),
        int(secrets.get("PORT")),
    )
    client.connect()
    time.sleep(5)
    client.join_channel("#preocts")
    while client.connected:
        while not client.read_queue_empty:
            message: str = client.read_next
            print(f"CONSOLE OUT >>> {message}")
            if message.startswith("PING"):
                print("PONG!")
                # client.send("PONG :" + message.split(":", 1)[1])
    client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()

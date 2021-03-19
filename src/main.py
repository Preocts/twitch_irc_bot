#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" WIP

Author: Preocts <preocts@preocts.com>
"""
import logging
from typing import Optional

from src.loadenv import LoadEnv
from src.ircclient import IRCClient
from src.model.message import Message

irc_client: Optional[IRCClient] = None


def message_handler(message: Message) -> None:
    """ Handle messages as they happen in IRC """
    if irc_client is None:
        raise Exception("Unepected call of handler without client!")
    print(f">>> {message.message}")
    if message.command == "PRIVMSG" and "travelcast_bot" in message.params:
        if message.content == "!exit":
            print("Shutdown!")
            irc_client.disconnect()


def main() -> None:
    """ Main yo """
    secrets = LoadEnv()
    secrets.load()
    irc_client = IRCClient(
        secrets.get("BOT_NAME"),
        secrets.get("BOT_OAUTH_TWITCH"),
        secrets.get("SERVER"),
        int(secrets.get("PORT")),
    )
    irc_client.join_channel("#travelcast_bot")
    irc_client.start(message_handler)


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()

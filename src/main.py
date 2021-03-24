#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" WIP

Author: Preocts <preocts@preocts.com>
"""
import logging

from src.loadenv import LoadEnv
from src.ircclient import IRCClient
from src.model.message import Message


class IRCBot:
    """ IRC Bot """

    keyring = LoadEnv()

    def __init__(self) -> None:
        """ INIT """
        self.keyring.load()
        self.irc_client = IRCClient(
            self.keyring.get("BOT_NAME"),
            self.keyring.get("BOT_OAUTH_TWITCH"),
            self.keyring.get("SERVER"),
            int(self.keyring.get("PORT")),
        )

    def run_bot(self) -> None:
        """ This starts a bot, is blocking """
        self.irc_client.start(self.message_handler)
        self.irc_client.disconnect()

    def message_handler(self, message: Message) -> None:
        """ Handle messages as they happen in IRC """
        # print(f">>> {message.message}")
        if message.command == "PRIVMSG" and "travelcast_bot" in message.params:
            if message.content == "!start":
                self.irc_client.send_to_channel("#travelcast_bot", "Starting now!")
            if message.content == "!exit":
                print("Shutdown!")
                self.irc_client.disconnect()


def main() -> None:
    """ Main yo """
    bot = IRCBot()
    bot.run_bot()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    main()

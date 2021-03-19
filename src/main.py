#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" WIP

Author: Preocts <preocts@preocts.com>
"""
import logging

from src.loadenv import LoadEnv
from src.ircclient import IRCClient


def sit_and_spin(client: IRCClient) -> None:
    """ Main process loop? """
    client.connect()
    while client.connected:
        while client.is_read_queue_empty:
            continue
        message = client.read_next()
        print(f"RAW OUT >>> {message.message}")
        if message.command == "PING":
            print("PONG!")
            client.send_to_server(f"PONG :{message.content}")
        if message.command == "PRIVMSG" and "travelcast_bot" in message.params:
            if message.content == "!exit":
                print("Shutdown!")
                client.disconnect()


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
    client.join_channel("#travelcast_bot")
    sit_and_spin(client)
    client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()

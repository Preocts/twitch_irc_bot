#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" WIP

Author: Preocts <preocts@preocts.com>
"""
import logging

from src.loadenv import LoadEnv
from src.ircclient import IRCClient


# TODO (preocts): We need a single loop that emits flags that alters behavior


def connect_to_twitch(client: IRCClient) -> None:
    """ Runs connection steps, authentication, and loads MOTD """
    seen_motd = False
    client.connect()
    while client.connected and not seen_motd:
        # Login loop, wait for MOTD
        while not client.is_read_queue_empty:
            message = client.read_next()
            print(f"RAW OUT >>> {message.message}")
            if message.command == "376":
                print("Seen MOTD")
                seen_motd = True


def sit_and_spin(client: IRCClient) -> None:
    """ Main process loop? """
    run_loop = True
    while client.connected and run_loop:
        # Getting things to work is so cludgy
        while not client.is_read_queue_empty:
            message = client.read_next()
            print(f"RAW OUT >>> {message.message}")
            if message.command == "PRIVMSG" and "travelcast_bot" in message.params:
                if message.content == "!exit":
                    print("Shutdown!")
                    run_loop = False
            if message.command == "PING":
                print("PONG!")
                client.send_to_server(f"PONG :{message.content}")


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
    connect_to_twitch(client)
    client.join_channel("#travelcast_bot")
    sit_and_spin(client)
    client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()

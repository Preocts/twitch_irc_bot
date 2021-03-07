#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" IRC Abstract layer designed for TwitchTV IRC chat

Author: Preocts <preocts@preocts.com>
"""
import time
import queue
import socket
import select
import logging
import threading

from src.loadenv import LoadEnv


# TODO (preocts): Config layer for these settings
READ_QUEUE_MAX_SIZE = 1_000
WRITE_QUEUE_MAX_SIZE = 1_000

# 500 character max including message tags
MAX_SEND_CHAR_SIZE = 500

# Max 15 messages in 30 seconds
WRITE_THROTTLE_MSG_COUNT = 15
WRITE_THROTTLE_SEC_SPAN = 30


class IRCConnect:
    """ Connection layer to IRC """

    logger = logging.getLogger(__name__)

    def __init__(
        self, nickname: str, password: str, server_url: str, port: int
    ) -> None:
        """ IRC connection """
        self.__read_queue: queue.Queue = queue.Queue(maxsize=READ_QUEUE_MAX_SIZE)
        self.__write_queue: queue.Queue = queue.Queue(maxsize=WRITE_QUEUE_MAX_SIZE)
        self.__socket_reader = threading.Thread(target=self.__socket_read_loop)
        self.__socket_writer = threading.Thread(target=self.__socket_write_loop)
        self.__socket_open = False
        self.__cfg = {
            "nick": nickname,
            "password": password,
            "url": server_url,
            "port": port,
        }
        self.irc_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @property
    def connected(self) -> bool:
        """ Returns True if IRC socket is open """
        return self.__socket_open

    @property
    def read_queue_empty(self) -> bool:
        """ Returns True if read queue is empty """
        return self.__read_queue.empty()

    @property
    def read_next(self) -> str:
        """ Returns next message in queue, does not check if queue is empty """
        return self.__read_queue.get(block=True, timeout=0.5)

    def auth_connection(self):
        """ Connect and authenticate """
        self.logger.info("Connecting and auth'ing to IRC server...")
        self.irc_client.connect((self.__cfg["url"], self.__cfg["port"]))
        self.irc_client.setblocking(False)
        self.logger.info("Connection established, authenticating...")

        self.__send(f"PASS {self.__cfg['password']}", False)
        self.__send(f"NICK {self.__cfg['nick']}")
        self.__send(
            f"USER {self.__cfg['nick']} {self.__cfg['nick']} {self.__cfg['nick']}"
        )
        self.__socket_open = True

    def connect(self) -> None:
        """ Connects to IRC and starts read/write threads. Blocking until complete """
        self.auth_connection()
        if self.connected:
            self.__socket_reader.start()
            self.__socket_writer.start()

    def disconnect(self) -> None:
        """ Closes connection and stops threads. Blocking until threads stop """
        self.irc_client.shutdown(socket.SHUT_RDWR)
        self.irc_client.close()
        self.__socket_open = False
        self.__socket_reader.join()
        self.__socket_writer.join()

    def send_to_server(self, message: str) -> str:
        """ Sends a message to the server, returns queued message """
        self.__write_queue.put(message[:MAX_SEND_CHAR_SIZE], block=True, timeout=0.5)
        return message[:MAX_SEND_CHAR_SIZE]

    def join_channel(self, channel_name: str) -> None:
        """ Join channel """
        self.send_to_server(f"JOIN {channel_name}")

    def __socket_read_loop(self, read_size: int = 512) -> None:
        """ Reads open socket, drops messages in queue, exits on socket close """
        self.logger.debug("Enter socket read loop. read_size: %s", read_size)
        remaining_seg = b""
        while self.__socket_open:
            read_list, _, _ = select.select([self.irc_client], [], [], 15)
            if not read_list:
                continue

            read_seg = self.__read(read_size)

            if read_seg:
                read_seg = remaining_seg + read_seg
                remaining_seg = self.__parse_lines_to_queue(read_seg)
            else:
                self.logger.warning("Read: Socket is closed!")
                self.__socket_open = False
        self.logger.debug("Exit socket read loop.")

    def __socket_write_loop(self) -> None:
        """ Writes queue'ed messages to open socket, exits on socket close """
        self.logger.debug("Enter socket write loop.")
        while self.__socket_open:
            if self.__write_queue.empty():
                continue
            message = self.__write_queue.get()
            self.__send(message[:MAX_SEND_CHAR_SIZE])
            # TODO: flood control
        self.logger.debug("Exit socket write loop")

    def __send(self, message: str, log: bool = True) -> None:
        """ Sends raw bytes, retries if blocked """
        self.logger.debug("Send message: %s", message if log else "***")
        while True:
            try:
                self.irc_client.send(f"{message}\r\n".encode("UTF-8"))
                break
            except BlockingIOError:
                self.logger.debug("Send blocked, retry...")
            except ConnectionResetError as err:
                self.logger.error("Send failed: %s", err)
                self.__socket_open = False

    def __read(self, read_size: int) -> bytes:
        """ Reads raw btyes, retries if blocked """
        while True:
            try:
                read_line = self.irc_client.recv(read_size)
                self.logger.debug("Read %s bytes", len(read_line))
                return read_line
            except BlockingIOError:
                self.logger.debug("Read blocked, retry...")
            except ConnectionResetError as err:
                self.logger.error("Send failed: %s", err)
                self.__socket_open = False
                return b""

    def __parse_lines_to_queue(self, read_seg: bytes) -> bytes:
        """ Add lines to read queue, returns overflow """
        message_string = read_seg.decode("UTF-8")
        message_lines = message_string.split("\n")
        overflow = message_lines.pop() if not message_string.endswith("\n") else ""

        for line in message_lines:
            if line:
                self.__read_queue.put(line, block=False, timeout=0.5)
        return overflow.encode("UTF-8")


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

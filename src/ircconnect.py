#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Let's build-a-bot """
import time
import queue
import socket
import logging
import threading
from typing import Optional

from src.loadenv import LoadEnv


READ_QUEUE_MAX_SIZE = 1_000


class IRCConnect:
    """ Connection layer to IRC """

    logger = logging.getLogger(__name__)

    def __init__(
        self, nickname: str, password: str, server_url: str, port: int
    ) -> None:
        """ IRC connection """
        self.read_messages: queue.Queue = queue.Queue(maxsize=READ_QUEUE_MAX_SIZE)
        self.__socket_reader = threading.Thread(target=self.__socket_read_loop)
        self.__thread_reader_flag = False
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
        """ Are we connected? """
        return self.__socket_open

    def auth_connection(self):
        """ Connect and authenticate """
        self.logger.info("Connecting and auth'ing to IRC server...")
        self.irc_client.connect((self.__cfg["url"], self.__cfg["port"]))

        self.logger.info("Connection established, authenticating...")
        self._send_raw(f"PASS {self.__cfg['password']}", False)
        self.logger.info("PASS sent...")
        self._send_raw(f"NICK {self.__cfg['nick']}")
        self.logger.info("NICK sent...")
        self._send_raw(
            f"USER {self.__cfg['nick']} {self.__cfg['nick']} {self.__cfg['nick']}"
        )
        self.logger.info("USER sent...")
        self.__socket_open = True

    def send(self, message: str) -> None:
        """ Sends a message """
        self._send_raw(message)

    def _send_raw(self, message: str, log: bool = True) -> None:
        """ Sends raw bytes """
        self.logger.debug("Send message: %s", message if log else "***")
        while True:
            try:
                self.irc_client.send(bytes(message + "\r\n", "UTF-8"))
                break
            except BlockingIOError:
                logging.debug("Retrying send...")
                time.sleep(0.25)

    def start_reader(self) -> None:
        """ Starts the socket reader thread """
        self.__thread_reader_flag = True
        self.__socket_reader.start()

    def stop_reader(self) -> None:
        """ Stops the socket reader thread """
        self.__thread_reader_flag = False
        self.__socket_reader.join()

    def __socket_read_loop(self, read_size: int = 512) -> None:
        """ Reads open socket, drops messages in queue, exits on socket close """
        self.logger.debug("Enter socket read loop. read_size: %s", read_size)
        overflow = b""
        self.irc_client.setblocking(False)
        while self.__thread_reader_flag:
            time.sleep(1)
            raw_read = self.__safe_read(read_size)
            if raw_read is None:
                continue
            if not raw_read:
                self.logger.warning("Read: Socket is closed!")
                self.__thread_reader_flag = False
                self.__socket_open = False
            elif overflow:
                raw_read = overflow + raw_read
            overflow = self.__parse_lines_to_queue(raw_read)
            self.logger.debug("Read %s bytes", len(raw_read))

    def __safe_read(self, read_size: int) -> Optional[bytes]:
        """ Catch for blocking """
        try:
            return self.irc_client.recv(read_size)
        except BlockingIOError:
            return None
        except ConnectionResetError:
            self.__thread_reader_flag = False
            self.__socket_open = False
            return None

    def __parse_lines_to_queue(self, raw_read: bytes) -> bytes:
        """ Add lines to read queue, returns overflow """
        message_string = raw_read.decode("UTF-8")
        message_lines = message_string.split("\n")
        overflow = message_lines.pop() if not message_string.endswith("\n") else ""

        for line in message_lines:
            self.read_messages.put(line)
        return overflow.encode("UTF-8")

    def join_channel(self, channel_name: str) -> None:
        """ Join channel """
        self.logger.debug("Joining: %s", channel_name)
        self._send_raw(f"JOIN {channel_name}")


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
    client.auth_connection()
    # client.join_channel("#preocts")
    client.start_reader()
    while client.connected:
        while not client.read_messages.empty():
            message: str = client.read_messages.get()
            print(message)
            if message.startswith("PING"):
                print("PONG!")
                client.send("PONG :" + message.split(":", 1)[1])
    client.stop_reader()
    client.irc_client.close()


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()

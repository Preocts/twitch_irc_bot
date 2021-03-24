#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" IRC Abstract layer designed for TwitchTV IRC chat

Author: Preocts <preocts@preocts.com>
"""
from __future__ import annotations

import time
import socket
import select
import logging
import threading
from queue import Queue
from queue import Empty
from typing import List
from typing import Optional
from typing import NamedTuple

from src.model.message import Message
from src.ircchannel import IRCChannel

# TODO (preocts): Config layer for these settings
READ_QUEUE_MAX_SIZE = 1_000
WRITE_QUEUE_MAX_SIZE = 1_000

# 500 character max including message tags
MAX_SEND_CHAR_SIZE = 500

# Max 20 messages in 30 seconds
WRITE_THROTTLE_MSG_COUNT = 20
WRITE_THROTTLE_SEC_SPAN = 30


class IRCClient:
    """ Connection layer to IRC """

    class ClientConfig(NamedTuple):
        """ Config and secrets for IRC Client """

        nickname: str
        password: Optional[str]
        url: str
        port: int
        wait_for_motd: bool

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        nickname: str,
        password: Optional[str],
        server_url: str,
        port: int,
        wait_for_motd: bool = True,
    ) -> None:
        """Create an IRC Client object

        Args:
            nickname: Name to use on the server
            pasasword: Password if used, set None to bypass
            server_url: IRC host server url
            port: Host port
            wait_for_motd: Defaulted True.
        """
        self.__channels: List[IRCChannel] = []
        self.__read_queue: Queue[Message] = Queue(maxsize=READ_QUEUE_MAX_SIZE)
        self.__socket_reader = threading.Thread(target=self.__socket_read_loop)
        self.__socket_writer = threading.Thread(target=self.__socket_write_loop)
        self.__socket_open = False
        self.__cfg = self.ClientConfig(
            nickname, password, server_url, port, wait_for_motd
        )
        self.irc_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @property
    def connected(self) -> bool:
        """ Returns True if IRC socket is open """
        return self.__socket_open

    def connect(self) -> None:
        """ Connects to IRC and starts read/write threads. Does not hold event loop """
        self.__create_socket()
        self.__channels.append(
            IRCChannel(
                "SYSTEM", WRITE_THROTTLE_MSG_COUNT, WRITE_THROTTLE_SEC_SPAN, True
            )
        )
        if self.connected:
            self.__socket_reader.start()
            self.__socket_writer.start()
        self.__authenticate()

    def __create_socket(self) -> None:
        """ Connect socket """
        self.logger.info("Connecting to IRC server...")
        self.irc_client.connect((self.__cfg.url, self.__cfg.port))
        self.irc_client.setblocking(False)
        self.logger.info("Connection established.")
        self.__socket_open = True

    def __authenticate(self) -> None:
        """ Queue authentication commands """
        if self.__cfg.password:
            self.send_to_server(f"PASS {self.__cfg.password}")
        self.send_to_server(f"NICK {self.__cfg.nickname}")
        self.send_to_server(
            f"USER {self.__cfg.nickname} {self.__cfg.nickname} {self.__cfg.nickname}"
        )

    def disconnect(self) -> None:
        """ Closes connection and stops threads. Blocking until threads stop """
        try:
            self.irc_client.shutdown(socket.SHUT_RDWR)
            self.irc_client.close()
        except OSError as err:
            self.logger.error(err)
        finally:
            self.logger.info("Waiting for threads to close, ~15 seconds...")
            self.__socket_open = False
            self.__socket_reader.join()
            self.__socket_writer.join()

    def send_to_server(self, message: str) -> None:
        """ Sends a message to the server, returns queued message """
        # Adds message to write SYS write queue, always active
        for channel in self.__channels:
            if channel.name == "SYSTEM":
                channel.send(Message.from_string(message))

    def send_to_channel(self, channel_name: str, message: str) -> None:
        """ Sends a message to the specific channel queue """
        for channel in self.__channels:
            if channel.name == channel_name:
                channel.send(Message.from_string(message))
                return
        self.logger.error("Not in channel: %s", channel)

    def join_channel(self, channel_name: str) -> None:
        """ Join channel """
        channels = [ch.name for ch in self.__channels]
        if channel_name in channels:
            self.logger.error("Already in channel: %s", channel_name)
        else:
            self.__channels.append(
                IRCChannel(
                    channel_name, WRITE_THROTTLE_MSG_COUNT, WRITE_THROTTLE_SEC_SPAN
                )
            )
            self.send_to_server(f"JOIN {channel_name}")

    def __socket_read_loop(self, read_size: int = 512) -> None:
        """ Reads open socket, drops messages in queue, exits on socket close """
        self.logger.debug("Enter socket read loop. read_size: %s", read_size)
        remaining_seg = b""
        while self.__socket_open:
            read_list, _, _ = select.select([self.irc_client], [], [], 15)
            if not read_list:
                continue

            try:
                read_segment = self.irc_client.recv(read_size)
                self.logger.debug("Read %s bytes", len(read_segment))
            except (ConnectionResetError, OSError) as err:
                self.logger.error("Send failed: %s", err)
                self.__socket_open = False
                break

            if read_segment:
                read_segment = remaining_seg + read_segment
                remaining_seg = self.__parse_read_segment(read_segment)
            else:
                self.logger.warning("Read: Socket is closed!")
                self.__socket_open = False
        self.logger.debug("Exit socket read loop.")

    def __parse_read_segment(self, read_segment: bytes) -> bytes:
        """ Routes system commands and add lines to read queue, returns overflow """
        message_lines = read_segment.decode("UTF-8").split("\r\n")
        overflow = message_lines.pop() if not message_lines[-1].endswith("\r\n") else ""

        for line in message_lines:
            if line:
                msg = Message.from_string(line)
                if msg.command == "PING":
                    self.logger.info("PING? PONG!")
                    self.send_to_server(f"PONG :{msg.content}")
                self.__read_queue.put(msg)
        return overflow.encode("UTF-8")

    def __socket_write_loop(self) -> None:
        """ Writes queue'ed messages to open socket, exits on socket close """
        self.logger.debug("Enter socket write loop.")
        while self.__socket_open:
            for channel in self.__channels:
                try:
                    message = channel.write_queue.get_nowait()
                except Empty:
                    continue
                self.__send(message.message)
        self.logger.debug("Exit socket write loop")

    def __send(self, message: str) -> None:
        """ Sends raw bytes, retries if blocked """
        self.logger.debug(
            "Send message: %s", message if "PASS" not in message else "PASS ***"
        )
        send_msg = f"{message}\r\n".encode("UTF-8")
        total_sent = 0
        while total_sent < len(send_msg) and self.__socket_open:
            try:
                sent_size = self.irc_client.send(send_msg[total_sent:])
                if not sent_size:
                    self.logger.warning("Write: Socket is closed!")
                    self.__socket_open = False
                total_sent += sent_size
            except BlockingIOError:
                self.logger.debug("Send blocked, retry...")
            except (ConnectionResetError, OSError) as err:
                self.logger.error("Send failed: %s", err)
                self.__socket_open = False
        self.logger.debug("Sent %s bytes.", len(message))

    def start(self, *args) -> None:
        """ Main process loop? """
        self.connect()
        time.sleep(4)
        self.join_channel("#travelcast_bot")
        while self.connected:
            try:
                message = self.__read_queue.get_nowait()
            except Empty:
                continue
            for channel in self.__channels:
                channel.handle_message(message)
            for arg in args:
                arg(message)

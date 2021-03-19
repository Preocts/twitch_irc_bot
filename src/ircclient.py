#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" IRC Abstract layer designed for TwitchTV IRC chat

Author: Preocts <preocts@preocts.com>
"""
from __future__ import annotations

import socket
import select
import logging
import threading
from queue import Queue
from queue import Empty
from typing import Dict

from src.model.message import Message

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

    logger = logging.getLogger(__name__)

    def __init__(
        self, nickname: str, password: str, server_url: str, port: int
    ) -> None:
        """ IRC connection """
        self.__read_queue: Queue[Message] = Queue(maxsize=READ_QUEUE_MAX_SIZE)
        self.__write_queue: Dict[str, Queue[Message]] = {}
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
        self.write_lock: bool = True

    @property
    def connected(self) -> bool:
        """ Returns True if IRC socket is open """
        return self.__socket_open

    @property
    def is_read_queue_empty(self) -> bool:
        """ Returns True if read queue is empty """
        return self.__read_queue.empty()

    def read_next(self) -> Message:
        """ Returns next message in queue, does not check if queue is empty """
        return self.__read_queue.get(block=True, timeout=0.25)

    def connect(self) -> None:
        """ Connects to IRC and starts read/write threads. Blocking until complete """
        self.__create_socket()
        self.__write_queue["SYS"] = Queue(WRITE_QUEUE_MAX_SIZE)
        if self.connected:
            self.__socket_reader.start()
            self.__socket_writer.start()
        self.__authenticate()

    def __create_socket(self) -> None:
        """ Connect socket """
        self.logger.info("Connecting to IRC server...")
        self.irc_client.connect((self.__cfg["url"], self.__cfg["port"]))
        self.irc_client.setblocking(False)
        self.logger.info("Connection established.")
        self.__socket_open = True

    def __authenticate(self) -> None:
        """ Queue authentication commands """
        self.send_to_server(f"PASS {self.__cfg['password']}")
        self.send_to_server(f"NICK {self.__cfg['nick']}")
        self.send_to_server(
            f"USER {self.__cfg['nick']} {self.__cfg['nick']} {self.__cfg['nick']}"
        )

    def disconnect(self) -> None:
        """ Closes connection and stops threads. Blocking until threads stop """
        try:
            self.irc_client.shutdown(socket.SHUT_RDWR)
            self.irc_client.close()
        except OSError as err:
            self.logger.error(err)
        finally:
            self.__socket_open = False
            self.__socket_reader.join()
            self.__socket_writer.join()

    def send_to_server(self, message: str) -> None:
        """ Sends a message to the server, returns queued message """
        # Adds message to write SYS write queue, always active
        self.__write_queue["SYS"].put(Message.from_string(message))

    def join_channel(self, channel_name: str) -> None:
        """ Join channel """
        if channel_name in self.__write_queue:
            self.logger.error("Already in channel: %s", channel_name)
        else:
            self.__write_queue[channel_name] = Queue(WRITE_QUEUE_MAX_SIZE)
            msg = Message.from_string(f"JOIN {channel_name}")
            self.__write_queue[channel_name].put(msg)

    def __socket_read_loop(self, read_size: int = 512) -> None:
        """ Reads open socket, drops messages in queue, exits on socket close """
        self.logger.debug("Enter socket read loop. read_size: %s", read_size)
        remaining_seg = b""
        while self.__socket_open:
            read_list, _, _ = select.select([self.irc_client], [], [], 15)
            if not read_list:
                continue

            try:
                read_seg = self.__read(read_size)
            except OSError as err:
                self.logger.error("Read error: %s, %s", err, self.__socket_open)
                continue

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
            for queue_name, writequeue in self.__write_queue.items():
                if queue_name != "SYS" and self.write_lock:
                    continue
                try:
                    message = writequeue.get(block=True, timeout=0.25)
                except Empty:
                    continue
                # TODO: flood control
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
        overflow = message_lines.pop() if not message_string.endswith("\r\n") else ""

        for line in message_lines:
            if line:
                msg = Message.from_string(line)
                self.__read_queue.put(msg)
                if self.write_lock:
                    self.write_lock = msg.command == "376"
                continue
        return overflow.encode("UTF-8")

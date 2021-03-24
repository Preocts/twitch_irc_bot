#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Represents the channel of an IRC connection

Author: Preocts <preocts@preocts.com>
"""
from __future__ import annotations

import queue
import logging

from src.model.message import Message
from src.decayingcounter import DecayingCounter


class IRCChannel:
    """ An IRC Channel for use in the IRCClient class """

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        channel_name: str,
        throttle_count: int,
        throttle_time: int,
        join_override: bool = False,
    ) -> None:
        """ Provide the name of the channel """
        self.name = channel_name
        self.write_queue: queue.Queue[Message] = queue.Queue()
        self.throttle: DecayingCounter = DecayingCounter(throttle_time, throttle_count)

        self.__namreply: bool = join_override
        self.__endofnames: bool = join_override

    def send(self, message: Message) -> None:
        """ Add a message to the write queue """
        if not self.__joined:
            return
        if self.throttle.inc_to_max(self.name):
            # TODO (preocts) Handle full queue
            self.write_queue.put_nowait(message)
        else:
            self.logger.warning(
                "Flood control on %s, dropping '%s'", self.name, message
            )

    def handle_message(self, message: Message) -> None:
        """Handles incoming message directed toward channel

        NOTE:
            Unlocks channel write queue when fully JOINED. This requires
            a completed 353 and 366 response from the IRC server.
        """
        if message.command == "353":
            self.__namreply = True
        if message.command == "366":
            self.__endofnames = True

        # TODO (preocts) Log/write message by channel name
        print(f"{self.name}>>> {message.message}")

    def __joined(self) -> bool:
        """ Returns true if joined to channel """
        return all([self.__namreply, self.__endofnames])

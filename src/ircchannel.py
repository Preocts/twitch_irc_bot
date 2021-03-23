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

WRITE_THROTTLE_MSG_COUNT = 20
WRITE_THROTTLE_SEC_SPAN = 30


class IRCChannel:
    """ An IRC Channel for use in the IRCClient class """

    logger = logging.getLogger(__name__)

    def __init__(self, channel_name: str) -> None:
        """ Provide the name of the channel """
        self.name = channel_name
        self.write_queue: queue.Queue[Message] = queue.Queue()
        self.write_locked: bool = True
        self.__namreply: bool = False
        self.__endofnames: bool = False

        self.throttle_count: int = WRITE_THROTTLE_MSG_COUNT
        self.throttle: DecayingCounter = DecayingCounter(WRITE_THROTTLE_SEC_SPAN)

    def queue_write(self, message: Message) -> None:
        """ Add a message to the write queue """
        if not self.__joined or self.write_locked:
            return
        if self.throttle.inc(self.name) >= self.throttle_count:
            self.logger.warning(
                "Flood control on %s, dropping '%s'", self.name, message
            )
            return
        self.write_queue.put(message, block=False, timeout=0.25)

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

    def __joined(self) -> bool:
        """ Returns true if joined to channel """
        return all([self.__namreply, self.__endofnames])

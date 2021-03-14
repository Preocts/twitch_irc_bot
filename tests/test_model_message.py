#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Unit tests for model: message.py

Author: Preocts <preocts@preocts.com>
"""
from src.model.message import Message


def test_basic_parse() -> None:
    """ MOTD message from server """
    mock = ":tmi.twitch.tv 372 my_bot :You are in a maze of twisty passages."
    message = Message.from_string(mock)
    assert message.prefix == ":tmi.twitch.tv"
    assert message.command == "372"
    assert message.params == "my_bot"
    assert message.content == ":You are in a maze of twisty passages."


def test_no_prefix_no_middle() -> None:
    """ Ensure pieces fall where they should when missing """
    mock = "PING :tmi.twitch.tv callback"
    message = Message.from_string(mock)
    assert message.prefix is None
    assert message.middle is None
    assert message.content == ":tmi.twitch.tv callback"


def test_no_trailing() -> None:
    """ Second half of ensuring pieces fall where they should """
    mock = ":my_bot!my_bot@my_bot.tmi.twitch.tv JOIN #my_bot params"
    message = Message.from_string(mock)
    assert message.trailing is None


def test_bad_message() -> None:
    """ Some data safety for broken, malformed messages """
    assert Message.from_string("break").command == "break"
    assert Message.from_string("")
    assert Message.from_string(": : : : : : : :  : : : : : :  ")

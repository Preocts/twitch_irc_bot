#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Data-type class to process IRC message by RFC 1459 standard

Author: Preocts <preocts@preocts.com>
"""
from __future__ import annotations

from typing import NamedTuple
from typing import Optional
from typing import Tuple


class Message(NamedTuple):
    """IRC message

    From RFC 1459:

    <message>  ::= [':' <prefix> <SPACE> ] <command> <params> <crlf>
    <prefix>   ::= <servername> | <nick> [ '!' <user> ] [ '@' <host> ]
    <command>  ::= <letter> { <letter> } | <number> <number> <number>
    <SPACE>    ::= ' ' { ' ' }
    <params>   ::= <SPACE> [ ':' <trailing> | <middle> <params> ]
    <middle>   ::= <Any *non-empty* sequence of octets not including SPACE
                or NUL or CR or LF, the first of which may not be ':'>
    <trailing> ::= <Any, possibly *empty*, sequence of octets not including
                    NUL or CR or LF>
    <crlf>     ::= CR LF
    """

    message: str = ""
    prefix: Optional[str] = None
    command: str = ""
    middle: Optional[Tuple[str, ...]] = None
    trailing: Optional[Tuple[str, ...]] = None

    @property
    def params(self) -> str:
        """ String return of message params (middle) """
        return " ".join(self.middle) if self.middle else ""

    @property
    def content(self) -> str:
        """ String return message content (trailing) """
        return (" ".join(self.trailing)).lstrip(":") if self.trailing else ""

    @classmethod
    def from_string(cls, message: str) -> Message:
        """ Create Message object from string """
        if not message:
            return cls()
        prefix = message.split()[0] if message.startswith(":") else None
        command = message.split()[1] if prefix else message.split()[0]
        params = message.split()[2:] if prefix else message.split()[1:]
        middle, trailing, idx = [None, None, 0]
        if params:
            for idx, param in enumerate(params):
                if param.startswith(":"):
                    break
            middle = (
                params[0:idx] if params[idx].startswith(":") else params[0 : idx + 1]
            )
            trailing = params[idx:] if params[idx].startswith(":") else []
        return cls(
            message=message,
            prefix=prefix,
            command=command,
            middle=tuple(middle) if middle else None,
            trailing=tuple(trailing) if trailing else None,
        )

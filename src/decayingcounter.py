#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" A class that holds items which die after N seconds

Author: Preocts <preocts@preocts.com>
"""
import datetime
from typing import List
from typing import Dict


class DecayingCounter:
    """ Tracks number of events within a given life_span of seconds """

    __slots__ = ["life_span", "__groups"]

    def __init__(self, life_span: int) -> None:
        """ Set life_span to the length of time, in seconds, items live in groups """
        self.life_span = datetime.timedelta(seconds=life_span)
        self.__groups: Dict[str, List[datetime.datetime]] = {}

    def inc(self, group_name: str) -> int:
        """ Increment a group by 1 (one) returns group size, create group if needed """
        self.__clean_group(group_name)
        if group_name not in self.__groups:
            self.__groups[group_name] = []
        self.__groups[group_name].insert(0, datetime.datetime.now())
        return len(self.__groups[group_name])

    def count(self, group_name: str) -> int:
        """ Returns count of group without incrementing it """
        self.__clean_group(group_name)
        return len(self.__groups[group_name]) if group_name in self.__groups else 0

    def __clean_group(self, group: str) -> None:
        """ Removes expired items from group """
        while len(self.__groups.get(group, [])):
            if (datetime.datetime.now() - self.__groups[group][-1]) > self.life_span:
                self.__groups[group].pop()
            else:
                break

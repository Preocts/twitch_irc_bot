#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" A class that holds items which die after N seconds

Author: Preocts <preocts@preocts.com>
"""
import datetime
from typing import List
from typing import Dict
from typing import Optional


class DecayingCounter:
    """ Tracks number of events within a given life_span of seconds """

    __slots__ = ["life_span", "__groups", "__max"]

    def __init__(self, life_span: int, max_count: Optional[int] = None) -> None:
        """ Set life_span to the length of time, in seconds, items live in groups """
        self.__max = max_count
        self.life_span = datetime.timedelta(seconds=life_span)
        self.__groups: Dict[str, List[datetime.datetime]] = {}

    def inc_to_max(self, group_name: str) -> bool:
        """ Increments group by 1 and return true. If max is reached, returns false """
        if self.__max is None:
            raise Exception("Using 'inc_to_max' with no max set.")
        if self.count(group_name) < self.__max:
            self.inc(group_name)
            return True
        else:
            return False

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
        while self.__groups.get(group, []):
            if (datetime.datetime.now() - self.__groups[group][-1]) > self.life_span:
                self.__groups[group].pop()
            else:
                break

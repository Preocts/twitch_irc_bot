#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Unit tests for decaying counter

Author: Preocts <preocts@preocts.com>
"""
import random
from string import ascii_letters
import datetime

from src.decayingcounter import DecayingCounter


def random_string() -> str:
    """ Returns random string of random length 1-24 characters """
    random.seed()
    return "".join(
        [random.choice(ascii_letters) for _ in range(0, random.randint(1, 24))]  # nosec
    )


class TestDecayingCounter:
    """ Test suite """

    groups = DecayingCounter(2)

    def test_two_second_check(self) -> None:
        """ Ensures we are decaying """
        while self.groups.count("mock") < 100:
            self.groups.inc("mock")
        wait_time = datetime.timedelta(seconds=2)
        tic = datetime.datetime.now()
        assert self.groups.count("mock") > 0
        while (datetime.datetime.now() - wait_time) < tic:
            pass
        assert self.groups.count("mock") == 0

    def test_names(self) -> None:
        """ Names shouldn't matter, should always get a count back """
        for idx in range(10_000):
            if idx % 2:
                assert self.groups.inc(random_string()) >= 1
            else:
                assert self.groups.count(random_string()) >= 0

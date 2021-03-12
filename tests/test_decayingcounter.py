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
        [random.choice(ascii_letters) for _ in range(0, random.randint(1, 24))]
    )


class TestDecayingCounter:
    """ Test suite """

    def test_two_second_check(self) -> None:
        """ Ensures we are decaying """
        groups = DecayingCounter(2)
        while groups.count("mock") < 100:
            groups.inc("mock")
        five_sec = datetime.timedelta(seconds=2)
        tic = datetime.datetime.now()
        assert groups.count("mock") > 0
        while (datetime.datetime.now() - five_sec) < tic:
            pass
        assert groups.count("mock") == 0

    def test_names(self) -> None:
        """ Names shouldn't matter, should always get a count back """
        groups = DecayingCounter(60)
        for idx in range(10_000):
            if idx % 2:
                assert groups.inc(random_string()) >= 1
            else:
                groups.count(random_string()) >= 0


if __name__ == "__main__":
    mylist = [random_string() for _ in range(10_000)]
    with open("random", "w") as outfile:
        for line in mylist:
            outfile.write(f"{line}\n")

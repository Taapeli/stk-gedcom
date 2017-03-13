#!/usr/bin/env python3
"""
Restores marked tags: <tag>-X -> <tag>
"""

_VERSION = "1.0"
from classes.gedcom_line import GedcomLine

def add_args(parser):
    pass

def initialize(args):
    pass

def phase3(args, gedline, f):
    if gedline.tag.endswith("-X"):
        gedline.tag = gedline.tag[:-2]
#       line = "{} {} {}".format(gedline.level, gedline.tag, gedline.value)
    f.emit(gedline.get_line())

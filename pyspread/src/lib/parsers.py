#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

parsers
=======

Provides
--------

 * get_font_from_data
 * get_pen_from_data
 * color2code
 * code2color
 * parse_dict_strings
 * is_svg

"""

try:
    import rsvg
    import glib
except ImportError:
    rsvg = None

import ast

import wx

from src.sysvars import get_default_font


def get_font_from_data(fontdata):
    """Returns wx.Font from fontdata string"""

    textfont = get_default_font()

    if fontdata != "":
        nativefontinfo = wx.NativeFontInfo()
        nativefontinfo.FromString(fontdata)

        # OS X does not like a PointSize of 0
        # Therefore, it is explicitly set to the system default font point size

        if not nativefontinfo.GetPointSize():
            nativefontinfo.SetPointSize(get_default_font().GetPointSize())

        textfont.SetNativeFontInfo(nativefontinfo)

    return textfont


def get_pen_from_data(pendata):
    """Returns wx.Pen from pendata attribute list"""

    pen_color = wx.Colour()
    pen_color.SetRGB(pendata[0])
    pen = wx.Pen(pen_color, *pendata[1:])
    pen.SetJoin(wx.JOIN_MITER)

    return pen


def code2color(color_string):
    """Returns wx.Colour from a string of a 3-tuple of floats in [0.0, 1.0]"""

    color_tuple = ast.literal_eval(color_string)
    color_tuple_int = [int(x * 255.0) for x in color_tuple]

    return wx.Colour(*color_tuple_int)


def color2code(color):
    """Returns repr of 3-tuple of floats in [0.0, 1.0] from wx.Colour"""

    return str(tuple(i / 255.0 for i in color.Get()))


def color_pack2rgb(packed):
    """Returns r, g, b tuple from packed wx.ColourGetRGB value"""

    r = packed & 255
    g = (packed & (255 << 8)) >> 8
    b = (packed & (255 << 16)) >> 16

    return r, g, b


def color_rgb2pack(r, g, b):
    """Returns packed wx.ColourGetRGB value from r, g, b tuple"""

    return r + (g << 8) + (b << 16)


def unquote_string(code):
    """Returns a string from code that contains aa repr of the string"""

    if code[0] in ['"', "'"]:
        start = 1
    else:
        # start may have a Unicode or raw string
        start = 2

    return code[start:-1]


def parse_dict_strings(code):
    """Generator of elements of a dict that is given in the code string

    Parsing is shallow, i.e. all content is yielded as strings

    Parameters
    ----------
    code: String
    \tString that contains a dict

    """

    i = 0
    level = 0
    chunk_start = 0
    curr_paren = None

    for i, char in enumerate(code):
        if char in ["(", "[", "{"] and curr_paren is None:
            level += 1
        elif char in [")", "]", "}"] and curr_paren is None:
            level -= 1
        elif char in ['"', "'"]:
            if curr_paren == char:
                curr_paren = None
            elif curr_paren is None:
                curr_paren = char

        if level == 0 and char in [':', ','] and curr_paren is None:
            yield code[chunk_start: i].strip()
            chunk_start = i + 1

    yield code[chunk_start:i + 1].strip()


def common_start(strings):
    """Returns start sub-string that is common for all given strings

    Parameters
    ----------
    strings: List of strings
    \tThese strings are evaluated for their largest common start string

    """

    def gen_start_strings(string):
        """Generator that yield start sub-strings of length 1, 2, ..."""

        for i in range(1, len(string) + 1):
            yield string[:i]

    # Empty strings list
    if not strings:
        return ""

    start_string = ""

    # Get sucessively start string of 1st string
    for start_string in gen_start_strings(max(strings)):
        if not all(string.startswith(start_string) for string in strings):
            return start_string[:-1]

    return start_string


def is_svg(code):
    """Checks if code is an svg image

    Parameters
    ----------
    code: String
    \tCode to be parsed in order to check svg complaince

    """

    if rsvg is None:
        return

    try:
        rsvg.Handle(data=code)

    except glib.GError:
        return False

    # The SVG file has to refer to its xmlns
    # Hopefully, it does so wiyhin the first 1000 characters

    if "http://www.w3.org/2000/svg" in code[:1000]:
        return True

    return False

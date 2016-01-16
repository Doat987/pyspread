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
test_parsers
============

Unit tests for parsers.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.lib.parsers import get_font_from_data, get_pen_from_data, common_start
from src.lib.parsers import color_pack2rgb, color_rgb2pack, is_svg

param_font = [
    {"fontdata": "Courier New 13", "face": "Courier New", "size": 13},
    {"fontdata": "Arial 43", "face": "Arial", "size": 43},
]


# In Windows, base fonts seem to have no face name
# Therefore, the following test fails
if "__WXMSW__" not in wx.PlatformInfo:

    @params(param_font)
    def test_get_font_from_data(fontdata, face, size):
        """Unit test for get_font_from_data"""

        try:
            font = get_font_from_data(fontdata)
        except:
            # msttcorefonts is missing
            return

        # This test seems to fail on many Linux systems because
        # font nemes are tweaked.
        # Since this has never been an issue, I comment out the face name test
        # assert font.GetFaceName() == face
        assert font.GetPointSize() == size

param_pen = [
    {"pendata": [wx.RED.GetRGB(), 4], "width": 4,
     "color": wx.Colour(255, 0, 0, 255)},
    {"pendata": [wx.BLUE.GetRGB(), 1], "width": 1,
     "color": wx.Colour(0, 0, 255, 255)},
    {"pendata": [wx.GREEN.GetRGB(), 0], "width": 0,
     "color": wx.Colour(0, 255, 0, 255)},
]


@params(param_pen)
def test_get_pen_from_data(pendata, width, color):
    """Unit test for get_pen_from_data"""

    pen = get_pen_from_data(pendata)

    assert pen.GetColour() == color
    assert pen.GetWidth() == width


param_color_pack2rgb = [
    {"pack": wx.RED.GetRGB(), "res": (255, 0, 0)},
    {"pack": wx.BLACK.GetRGB(), "res": (0, 0, 0)},
    {"pack": wx.WHITE.GetRGB(), "res": (255, 255, 255)},
    {"pack": wx.Colour(34, 12, 42).GetRGB(), "res": (34, 12, 42)},
]


@params(param_color_pack2rgb)
def test_color_pack2rgb(pack, res):
    """Unit test for color_pack2rgb"""

    assert color_pack2rgb(pack) == res


param_color_rgb2pack = [
    {"rgb": (255, 0, 0), "res": wx.RED.GetRGB()},
    {"rgb": (0, 0, 0), "res": wx.BLACK.GetRGB()},
    {"rgb": (255, 255, 255), "res": wx.WHITE.GetRGB()},
    {"rgb": (34, 12, 42), "res": wx.Colour(34, 12, 42).GetRGB()},
]


@params(param_color_rgb2pack)
def test_color_rgb2pack(rgb, res):
    """Unit test for rgb2pack"""

    assert color_rgb2pack(*rgb) == res


param_common_start = [
    {"strings": [], "res": ""},
    {"strings": ["", ""], "res": ""},
    {"strings": [""] * 100, "res": ""},
    {"strings": ["test", "test"], "res": "test"},
    {"strings": ["test", "test"], "res": "test"},
    {"strings": ["te", "tl"], "res": "t"},
    {"strings": ["1", "tl"], "res": ""},
    {"strings": ["split", "splitlines"], "res": "split"},
]


@params(param_common_start)
def test_common_start(strings, res):
    """Unit test for common_start"""

    __res = common_start(strings)

    assert res == __res


param_is_svg = [
    {"code": "", "res": False},
    {"code": "sdjkl;fhsd", "res": False},
    {"code": open(TESTPATH + "test1.svg").read(), "res": True},
]


@params(param_is_svg)
def test_is_svg(code, res):
    """Unit test for is_svg"""

    if is_svg(code) is not None:
        # This only works if pyrsvg is installed
        assert is_svg(code) == res

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
test_clipboard
==============

Unit tests for clipboard.py

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

from src.lib.clipboard import Clipboard


class TestClipboard(object):
    """Unit tests for Clipboard"""

    clipboard = Clipboard()

    param_convert_clipboard = [
        {'data': "1\t2\t3", 'sep': "\t", 'res': [['1', '2', '3']]},
        {'data': "1\t2\t3\n4\t5\t6", 'sep': "\t",
         'res': [['1', '2', '3'], ['4', '5', '6']]},
        {'data': "1,2,3\n4,5,6", 'sep': ",",
         'res': [['1', '2', '3'], ['4', '5', '6']]},
    ]

    @params(param_convert_clipboard)
    def test_convert_clipboard(self, data, sep, res):
        """Unit test for _convert_clipboard"""

        gengen = self.clipboard._convert_clipboard(data, sep)
        result = list(list(linegen) for linegen in gengen)

        assert result == res

    param_set_get_clipboard = [
        {'text': ""},
        {'text': "Test"},
        {'text': "ÓÓó€ëáßðïœ"},
        {'text': "Test1\tTest2"},
        {'text': "\b"},
    ]

    @params(param_set_get_clipboard)
    def test_set_get_clipboard(self, text):
        """Unit test for get_clipboard and set_clipboard"""

        clipboard = wx.TheClipboard

        textdata = wx.TextDataObject()
        textdata.SetText(text)
        clipboard.Open()
        clipboard.SetData(textdata)
        clipboard.Close()

        assert self.clipboard.get_clipboard() == text

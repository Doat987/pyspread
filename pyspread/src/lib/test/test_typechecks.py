#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit test for typechecks.py"""

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
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.lib.typechecks import is_slice_like, is_string_like, is_generator_like

param_slc = [
    {"slc": slice(None, None, None), "res": True},
    {"slc": slice(None, 4, 34), "res": True},
    {"slc": -2, "res": False},
    {"slc": [1, 2, 3], "res": False},
    {"slc": (1, 2, 3), "res": False},
    {"slc": {}, "res": False},
    {"slc": None, "res": False},
]


@params(param_slc)
def test_is_slice_like(slc, res):
    """Unit test for is_slice_like"""

    assert is_slice_like(slc) == res

param_str = [
    {"string": "", "res": True},
    {"string": "", "res": True},
    {"string": "Test", "res": True},
    {"string": "x" * 1000, "res": True},
    {"string": ['1'], "res": False},
    {"string": ('1', '2', '3'), "res": False},
    {"string": {None: '3'}, "res": False},
    {"string": None, "res": False},
]


@params(param_str)
def test_is_string_like(string, res):
    """Unit test for is_string_like"""

    assert is_string_like(string) == res

param_gen = [
    {"gen": (i for i in [3, 4]), "res": True},
    {"gen": (str(i) for i in range(1000)), "res": True},
    {"gen": ((2, 3) for _ in range(10)), "res": True},
    {"gen": "x" * 1000, "res": False},
    {"gen": ['1'], "res": False},
    {"gen": ('1', '2', '3'), "res": False},
    {"gen": {None: '3'}, "res": False},
    {"gen": None, "res": False},
]


@params(param_gen)
def test_is_generator_like(gen, res):
    """Unit test for is_generator_like"""

    assert is_generator_like(gen) == res

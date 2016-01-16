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
test_csv
========

Unit tests for __csv.py

"""

import os
import sys
import types

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.testlib import params, pytest_generate_tests
import src.lib.__csv as __csv
from src.lib.__csv import Digest, CsvInterface, TxtGenerator, sniff

param_sniff = [
    {'filepath': TESTPATH + 'test1.csv', 'header': True, 'delimiter': ',',
     'doublequote': 0, 'quoting': 0, 'quotechar': '"',
     'lineterminator': "\r\n", 'skipinitialspace': 0},
]


@params(param_sniff)
def test_sniff(filepath, header, delimiter, doublequote, quoting, quotechar,
               lineterminator, skipinitialspace):
    """Unit test for sniff"""

    dialect, __header = __csv.sniff(filepath)
    assert __header == header
    assert dialect.delimiter == delimiter
    assert dialect.doublequote == doublequote
    assert dialect.quoting == quoting
    assert dialect.quotechar == quotechar
    assert dialect.lineterminator == lineterminator
    assert dialect.skipinitialspace == skipinitialspace


param_first_line = [
    {'filepath': TESTPATH + 'test1.csv',
     'first_line': ["Text", "Number", "Float", "Date"]},
]


@params(param_first_line)
def test_get_first_line(filepath, first_line):
    """Unit test for get_first_line"""

    dialect, __header = __csv.sniff(filepath)
    __first_line = __csv.get_first_line(filepath, dialect)

    assert __first_line == first_line


param_digested_line = [
    {'line': "1, 3, 1",
     'digest_types': [bytes, int, float],
     'res': ["1", 3, 1.0]},
    {'line': "1",
     'digest_types': [float],
     'res': [1.0]},
    {'line': "1, Gsdfjkljö",
     'digest_types': [float, str],
     'res': [1.0, "Gsdfjkljö"]},
]


@params(param_digested_line)
def digested_line(line, digest_types, res):
    """Unit test for digested_line"""

    assert __csv.digested_line(line, digest_types) == res


def test_cell_key_val_gen():
    """Unit test for cell_key_val_gen"""

    list_of_lists = [list(range(10)), list(range(10))]
    gen = __csv.cell_key_val_gen(list_of_lists, (100, 100, 10))
    for row, col, value in gen:
        assert col == value


class TestDigest(object):
    """Unit tests for Digest"""

    param_make_string = [
        {'val': 1, 'acc_types': [bytes], 'res': "1"},
        {'val': None, 'acc_types': [bytes], 'res': ""},
        {'val': 1, 'acc_types': [str], 'res': "1"},
        {'val': None, 'acc_types': [str], 'res': ""},
    ]

    @params(param_make_string)
    def test_make(self, val, acc_types, res):
        """Unit test for make_foo"""

        digest = Digest(acc_types)

        assert digest(val) == res
        assert type(digest(val)) is type(res)


class TestCsvInterface(object):
    """Unit tests for CsvInterface"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        filepath = TESTPATH + 'test1.csv'
        self.dialect, __ = sniff(filepath)
        self.digest_types = [str]
        has_header = True

        self.interface = CsvInterface(self.main_window, filepath, self.dialect,
                                      self.digest_types, has_header)

#    def test_iter(self):
#        """Unit test for __iter__"""
#
#        testline = [u"Test1", u"234", u"3.34", u"2012/12/04"]
#
#        for i, line in enumerate(self.interface):
#            if i:
#                for j, ele in enumerate(line):
#                    assert ele == repr(testline[j])

    def test_get_csv_cells_gen(self):
        """Unit test for _get_csv_cells_gen"""

        data = ['324', '234', 'sdfg']
        res = self.interface._get_csv_cells_gen(data)

        for ele, rele in zip(data, res):
            assert repr(ele) == rele

    def test_write(self):
        """Unit test for write"""

        filepath = TESTPATH + 'dummy.csv'
        interface = CsvInterface(self.main_window, filepath, self.dialect,
                                 self.digest_types, False)

        interface.write([["test", "world"], ["", "hello"]])

        dummy = open(filepath, "w")
        interface.write(["test", "world"])
        dummy.close()

        os.remove(filepath)


class TestTxtGenerator(object):
    """Unit tests for TxtGenerator"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        filepath = TESTPATH + 'test_txt.csv'
        self.txtgen = TxtGenerator(self.main_window, filepath)

    def test_iter(self):
        """Unit test for __iter__"""

        res = [[ele for ele in line] for line in self.txtgen]
        assert res == [["Hallo", "Welt"], ["Test", "2"]]

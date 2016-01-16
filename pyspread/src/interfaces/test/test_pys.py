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
test_pys
========

Unit tests for pys.py

"""

import bz2
import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.interfaces.pys import Pys
from src.lib.selection import Selection
from src.lib.testlib import params, pytest_generate_tests
from src.model.model import CodeArray


class TestPys(object):
    """Unit tests for Pys"""

    def setup_method(self, method):
        """Creates Pys class with code_array and temporary test.pys file"""

        # All data structures are initially empty
        # The test file pys_file has entries in each category

        self.code_array = CodeArray((1000, 100, 3))
        self.pys_infile = bz2.BZ2File(TESTPATH + "pys_test1.pys")
        self.pys_outfile_path = TESTPATH + "pys_test2.pys"
        self.pys_in = Pys(self.code_array, self.pys_infile)

    def write_pys_out(self, method_name, *args, **kwargs):
        """Helper that writes an pys_out file"""

        outfile = bz2.BZ2File(self.pys_outfile_path, "w")
        pys_out = Pys(self.code_array, outfile)
        method = getattr(pys_out, method_name)
        method(*args, **kwargs)
        outfile.close()

    def read_pys_out(self):
        """Returns string of pys_out content and removes pys_out"""

        outfile = bz2.BZ2File(self.pys_outfile_path)
        res = outfile.read()
        outfile.close()

        # Clean up the test dir
        os.remove(self.pys_outfile_path)

        return res

    param_split_tidy = [
        {'string': "1", 'maxsplit': None, 'res': ["1"]},
        {'string': "1\t2", 'maxsplit': None, 'res': ["1", "2"]},
        {'string': "1\t2\n", 'maxsplit': None, 'res': ["1", "2"]},
        {'string': "1\t2\t3", 'maxsplit': 1, 'res': ["1", "2\t3"]},
        {'string': "1\t2\t3\n", 'maxsplit': 1, 'res': ["1", "2\t3"]},
    ]

    @params(param_split_tidy)
    def test_split_tidy(self, string, maxsplit, res):
        """Test _split_tidy method"""

        assert self.pys_in._split_tidy(string, maxsplit) == res

    param_get_key = [
        {'keystrings': ["1", "2", "3"], 'res': (1, 2, 3)},
        {'keystrings': ["0", "0", "0"], 'res': (0, 0, 0)},
        {'keystrings': ["0", "0"], 'res': (0, 0)},
        {'keystrings': ["-2", "-2", "23"], 'res': (-2, -2, 23)},
        {'keystrings': list(map(str, range(100))), 'res': tuple(range(100))},
        {'keystrings': list(map(str, range(100))), 'res': tuple(range(100))},
    ]

    @params(param_get_key)
    def test_get_key(self, keystrings, res):
        """Test _get_key method"""

        assert self.pys_in._get_key(*keystrings) == res

    param_pys_assert_version = [
        {'line': "\n", 'res': False},
        {'line': "0.1\n", 'res': True},
        {'line': "1.0\n", 'res': True},
        {'line': "1.1\n", 'res': False},
    ]

    @params(param_pys_assert_version)
    def test_pys_assert_version(self, line, res):
        """Test _pys_assert_version method"""

        try:
            self.pys_in._pys_assert_version(line)
            assert res

        except ValueError:
            assert not res

    def test_version2pys(self):
        """Test _version2pys method"""

        self.write_pys_out("_version2pys")
        assert self.read_pys_out() == "0.1\n"

    param_shape2pys = [
        {'shape': (1000, 100, 3), 'res': "1000\t100\t3\n"},
        {'shape': (1, 1, 1), 'res': "1\t1\t1\n"},
        {'shape': (1000000, 1000000, 2), 'res': "1000000\t1000000\t2\n"},
    ]

    @params(param_shape2pys)
    def test_shape2pys(self, shape, res):
        """Test _shape2pys method"""

        self.code_array.dict_grid.shape = shape
        self.write_pys_out("_shape2pys")
        assert self.read_pys_out() == res

    @params(param_shape2pys)
    def test_pys2shape(self, res, shape):
        """Test _pys2shape method"""

        self.pys_in._pys2shape(res)
        assert self.code_array.dict_grid.shape == shape

    param_code2pys = [
        {'code': "0\t0\t0\tTest\n", 'key': (0, 0, 0), 'val': "Test"},
        {'code': "10\t0\t0\t" + "öäüß".encode("utf-8") + "\n",
         'key': (10, 0, 0), 'val': "öäüß"},
        {'code': "2\t0\t0\tTest\n", 'key': (2, 0, 0), 'val': "Test"},
        {'code': "2\t0\t0\t" + "a" * 100 + '\n', 'key': (2, 0, 0),
         'val': "a" * 100},
        {'code': '0\t0\t0\t"Test"\n', 'key': (0, 0, 0), 'val': '"Test"'},
    ]

    @params(param_code2pys)
    def test_code2pys(self, key, val, code):
        """Test _code2pys method"""

        self.code_array[key] = val
        self.write_pys_out("_code2pys")
        res = self.read_pys_out()

        assert res == code

    @params(param_code2pys)
    def test_pys2code(self, val, code, key):
        """Test _pys2code method"""

        self.pys_in._pys2code(code)
        assert self.code_array(key) == val

    param_attributes2pys = [
        {'code': "[]\t[]\t[]\t[]\t[(3, 4)]\t0\t'borderwidth_bottom'\t42\n",
         'selection': Selection([], [], [], [], [(3, 4)]), 'table': 0,
         'key': (3, 4, 0), 'attr': 'borderwidth_bottom', 'val': 42},
    ]

    @params(param_attributes2pys)
    def test_attributes2pys(self, selection, table, key, attr, val, code):
        """Test _attributes2pys method"""

        self.code_array.dict_grid.cell_attributes.undoable_append(
            (selection, table, {attr: val}), mark_unredo=False)

        self.write_pys_out("_attributes2pys")
        assert self.read_pys_out() == code

    @params(param_attributes2pys)
    def test_pys2attributes(self, selection, table, key, attr, val, code):
        """Test _pys2attributes method"""

        self.pys_in._pys2attributes(code)

        attrs = self.code_array.dict_grid.cell_attributes[key]
        assert attrs[attr] == val

    param_row_heights2pys = [
        {'row': 0, 'tab': 0, 'height': 0.1, 'code': "0\t0\t0.1\n"},
        {'row': 0, 'tab': 0, 'height': 0.0, 'code': "0\t0\t0.0\n"},
        {'row': 10, 'tab': 0, 'height': 1.0, 'code': "10\t0\t1.0\n"},
        {'row': 10, 'tab': 1, 'height': 1.0, 'code': "10\t1\t1.0\n"},
        {'row': 10, 'tab': 2, 'height': 100.0, 'code': "10\t2\t100.0\n"},
    ]

    @params(param_row_heights2pys)
    def test_row_heights2pys(self, row, tab, height, code):
        """Test _row_heights2pys method"""

        self.code_array.dict_grid.row_heights[(row, tab)] = height
        self.write_pys_out("_row_heights2pys")
        assert self.read_pys_out() == code

    @params(param_row_heights2pys)
    def test_pys2row_heights(self, row, tab, height, code):
        """Test _pys2row_heights method"""

        self.pys_in._pys2row_heights(code)
        assert self.code_array.dict_grid.row_heights[(row, tab)] == height

    param_col_widths2pys = [
        {'col': 0, 'tab': 0, 'width': 0.1, 'code': "0\t0\t0.1\n"},
        {'col': 0, 'tab': 0, 'width': 0.0, 'code': "0\t0\t0.0\n"},
        {'col': 10, 'tab': 0, 'width': 1.0, 'code': "10\t0\t1.0\n"},
        {'col': 10, 'tab': 1, 'width': 1.0, 'code': "10\t1\t1.0\n"},
        {'col': 10, 'tab': 2, 'width': 100.0, 'code': "10\t2\t100.0\n"},
    ]

    @params(param_col_widths2pys)
    def test_col_widths2pys(self, col, tab, width, code):
        """Test _col_widths2pys method"""

        self.code_array.dict_grid.col_widths[(col, tab)] = width
        self.write_pys_out("_col_widths2pys")
        assert self.read_pys_out() == code

    @params(param_col_widths2pys)
    def test_pys2col_widths(self, col, tab, width, code):
        """Test _pys2col_widths method"""

        self.pys_in._pys2col_widths(code)
        assert self.code_array.dict_grid.col_widths[(col, tab)] == width

    param_macros2pys = [
        {'code': "Test"},
        {'code': ""},
        {'code': "Test1\nTest2"},
        {'code': "öäüß"},
    ]

    @params(param_macros2pys)
    def test_macros2pys(self, code):
        """Test _macros2pys method"""

        self.code_array.dict_grid.macros = code
        self.write_pys_out("_macros2pys")
        res = self.read_pys_out().decode("utf-8")
        assert res == code

    @params(param_macros2pys)
    def test_pys2macros(self, code):
        """Test _pys2macros method"""

        self.pys_in._pys2macros(code.encode("utf-8"))
        assert self.code_array.dict_grid.macros == code

    def test_from_code_array(self):
        """Test from_code_array method"""

        self.pys_infile.seek(0)
        self.pys_in.to_code_array()

        outfile = bz2.BZ2File(self.pys_outfile_path, "w")
        pys_out = Pys(self.code_array, outfile)
        pys_out.from_code_array()
        outfile.close()

        self.pys_infile.seek(0)
        in_data = self.pys_infile.read()

        outfile = bz2.BZ2File(self.pys_outfile_path)
        out_data = outfile.read()
        outfile.close()

        # Clean up the test dir
        os.remove(self.pys_outfile_path)

        assert in_data == out_data

    def test_to_code_array(self):
        """Test to_code_array method"""

        self.pys_in.to_code_array()

        assert self.code_array((0, 0, 0)) == '"Hallo"'

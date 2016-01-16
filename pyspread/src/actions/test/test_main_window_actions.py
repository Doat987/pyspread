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
test_self.main_window_actions.py
===========================

Unit tests for _self.main_window_actions.py

"""

import csv
import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.selection import Selection
from src.lib.testlib import grid_values, restore_basic_grid
from src.lib.testlib import params, pytest_generate_tests, basic_setup_test

from src.actions._main_window_actions import CsvInterface, TxtGenerator


class TestCsvInterface(object):
    def setup_method(self, method):
        self.main_window = MainWindow(None, title="pyspread", S=None)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        self.test_filename = TESTPATH + "test.csv"
        self.test_filename2 = TESTPATH + "test_one_col.csv"
        self.test_filename3 = TESTPATH + "test_write.csv"

    def _get_csv_gen(self, filename, digest_types=None):
        test_file = open(filename)
        dialect = csv.Sniffer().sniff(test_file.read(1024))
        test_file.close()

        if digest_types is None:
            digest_types = [type(1)]

        has_header = False

        return CsvInterface(self.main_window, filename,
                            dialect, digest_types, has_header)

    def test_get_csv_cells_gen(self):
        """Tests generator from csv content"""

        csv_gen = self._get_csv_gen(self.test_filename)

        column = range(100)

        cell_gen = csv_gen._get_csv_cells_gen(column)

        for i, cell in enumerate(cell_gen):
            assert str(i) == cell

## Test iter somehow stalls py.test
#    def test_iter(self):
#        """Tests csv generator"""
#
#        csv_gen = self._get_csv_gen(self.test_filename)
#
#        assert [list(col) for col in csv_gen] == [['1', '2'], ['3', '4']]
#
#        csv_gen2 = self._get_csv_gen(self.test_filename2,
#                                     digest_types=[type("")])
#
#        for i, col in enumerate(csv_gen2):
#            list_col = list(col)
#            if i < 6:
#                assert list_col == ["'" + str(i + 1) + "'", "''"]
#            else:
#                assert list_col == ["''", "''"]

    def test_write(self):
        """Tests writing csv file"""

        csv_gen = self._get_csv_gen(self.test_filename)
        csv_gen.path = self.test_filename3

        csv_gen.write(range(100) for _ in range(100))

        infile = open(self.test_filename3)
        content = infile.read()
        assert content[:10] == "0\t1\t2\t3\t4\t"
        infile.close()


class TestTxtGenerator(object):
    """Tests generating txt files"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        self.test_filename = TESTPATH + "test.csv"
        self.test_filename_single_col = TESTPATH + "large.txt"
        self.test_filename_notthere = TESTPATH + "notthere.txt"
        self.test_filename_bin = TESTPATH + "test1.pys"

    def test_iter(self):
        """Tests iterating over text files"""

        # Correct file with 2 columns

        txt_gen = TxtGenerator(self.main_window, self.test_filename)

        res = [['1', '2'], ['3', '4']]
        assert list(list(line_gen) for line_gen in txt_gen) == res

        # Correct file with 1 column

        txt_gen = TxtGenerator(self.main_window, self.test_filename_single_col)

        txt_list = []
        for i, line_gen in enumerate(txt_gen):
            txt_list.append(list(line_gen))
            if i == 3:
                break
        assert txt_list == [['00'], ['877452769922012304'],
                            ['877453769923767209'], ['877454769925522116']]

        # Missing file

        txt_gen = TxtGenerator(self.main_window, self.test_filename_notthere)
        assert list(txt_gen) == []

        # Binary file

        txt_gen = TxtGenerator(self.main_window, self.test_filename_bin)

        has_value_error = False

        try:
            print([list(ele) for ele in txt_gen])

        except ValueError:
            has_value_error = True

        ##TODO: This still fails and I do not know how to identify binary files
        ##assert has_value_error # ValueError should occur on binary file


class TestExchangeActions(object):
    """Does nothing because of User interaction in this method"""

    pass


class TestPrintActions(object):
    """Does nothing because of User interaction in this method"""

    pass


class TestClipboardActions(object):
    """Clipboard actions test class. Does not use actual clipboard."""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_copy = [
        {'selection': Selection([], [], [], [], [(0, 0)]), 'result': "'Test'"},
        {'selection': Selection([], [], [], [], [(999, 0)]), 'result': "1"},
        {'selection': Selection([], [], [], [], [(999, 99)]),
         'result': "$^%&$^"},
        {'selection': Selection([], [], [], [], [(0, 1)]),
         'result': "1"},
        {'selection': Selection([(0, 1)], [(0, 1)], [], [], []),
         'result': "1"},
        {'selection': Selection([(0, 1)], [(1, 1)], [], [], []),
         'result': "1\n3"},
        {'selection': Selection([(0, 1)], [(1, 2)], [], [], []),
         'result': "1\t2\n3\t4"},
    ]

    @params(param_copy)
    def test_cut(self, selection, result):
        """Test cut, i. e. copy and deletion"""

        restore_basic_grid(self.grid)

        assert self.main_window.actions.cut(selection) == result

        (top, left), (bottom, right) = selection.get_bbox()

        for row in range(top, bottom + 1):
            for col in range(left, right + 1):
                if (row, col) in selection:
                    key = row, col, 0
                    assert self.code_array[key] is None
                    self.code_array[key] = grid_values[key]

    @params(param_copy)
    def test_copy(self, selection, result):
        """Test copy of single values, lists and matrices"""

        restore_basic_grid(self.grid)

        assert self.main_window.actions.copy(selection) == result

    param_copy_result = [
        {'selection': Selection([], [], [], [], [(0, 0)]), 'result': "Test"},
        {'selection': Selection([], [], [], [], [(999, 0)]), 'result': "1"},
        {'selection': Selection([], [], [], [], [(999, 99)]),
         'result': "invalid syntax (<unknown>, line 1)"},
    ]

    @params(param_copy_result)
    def test_copy_result(self, selection, result):
        """Test copy results of single values, lists and matrices"""

        restore_basic_grid(self.grid)

        assert self.main_window.actions.copy_result(selection) == result

#    param_paste = [
#        {'target': (0, 0), 'data': "1",
#         'test_key': (0, 0, 0), 'test_val': "1"},
#        {'target': (25, 25), 'data': "1\t2",
#         'test_key': (25, 25, 0), 'test_val': "1"},
#        {'target': (25, 25), 'data': "1\t2",
#         'test_key': (25, 26, 0), 'test_val': "2"},
#        {'target': (25, 25), 'data': "1\t2",
#         'test_key': (26, 25, 0), 'test_val': None},
#        {'target': (25, 25), 'data': "1\t2\n3\t4",
#         'test_key': (25, 25, 0),  'test_val': "1"},
#        {'target': (25, 25), 'data': "1\t2\n3\t4",
#         'test_key': (25, 26, 0),  'test_val': "2"},
#        {'target': (25, 25), 'data': "1\t2\n3\t4",
#         'test_key': (26, 25, 0),  'test_val': "3"},
#        {'target': (27, 27), 'data': u"ä",
#         'test_key': (27, 27, 0), 'test_val': u"ä"},
#    ]
#
#    @params(param_paste)
#    def test_paste(self, target, data, test_key, test_val):
#        """Test paste of single values, lists and matrices"""
#
#        basic_setup_test(self.grid, self.main_window.actions.paste,
#                         test_key, test_val, target, data)


class TestMacroActions(object):
    """Unit tests for macro actions"""

    macros = "def f(x): return x * x"

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    def test_replace_macros(self):
        self.main_window.actions.replace_macros(self.macros)

        assert self.main_window.grid.code_array.macros == self.macros
        self.main_window.actions.replace_macros("")

    def test_execute_macros(self):

        # Unsure how to test since macros are not global in py.test

        pass

    param_open_macros = [
        {'filename': TESTPATH + "macrotest2.py"},
    ]

    @params(param_open_macros)
    def test_open_macros(self, filename):

        testmacro_infile = open(filename)
        testmacro_string = "\n" + testmacro_infile.read()
        testmacro_infile.close()

        self.main_window.actions.open_macros(filename)

        macros = self.main_window.grid.code_array.macros

        assert testmacro_string == macros
        assert self.main_window.grid.code_array.safe_mode

    def test_save_macros(self):
        """Unit tests for save_macros"""

        filepath = TESTPATH + "macro_dummy.py"

        macros = "Test"

        self.main_window.actions.save_macros(filepath, macros)
        macro_file = open(filepath)
        assert macros == macro_file.read()
        macro_file.close()
        os.remove(filepath)

        macro_file = open(filepath, "w")
        self.main_window.actions.save_macros(filepath, macros)
        macro_file.close()
        os.remove(filepath)


class TestHelpActions(object):
    """Does nothing because of User interaction in this method"""

    pass

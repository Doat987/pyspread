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
test_grid_cell_actions
======================

Unit tests for _grid_cell_actions.py

"""

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

from src.lib.testlib import params, pytest_generate_tests


class TestCellActions(object):
    """Cell actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, title="pyspread", S=None)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_set_code = [
        {'key': (0, 0, 0), 'code': "'Test'", 'result': "'Test'"},
        {'key': (0, 0, 0), 'code': "", 'result': None},
        {'key': (0, 0, 1), 'code': None, 'result': None},
        {'key': (999, 99, 2), 'code': "4", 'result': "4"},
    ]

    @params(param_set_code)
    def test_set_code(self, key, code, result):
        """Unit test for set_code"""

        self.main_window.changed_since_save = False

        self.grid.actions.set_code(key, code)

        assert self.grid.code_array(key) == result

    @params(param_set_code)
    def test_quote_code(self, key, code, result):
        """Unit test for quote_code"""

        self.grid.actions.set_code(key, code)
        self.grid.actions.quote_code(key)

        if code and code[0] not in ['"', "'"] and code[-1] not in ['"', "'"]:
            assert self.grid.code_array(key) == 'u"' + code + '"'
        elif code and code is not None:
            assert self.grid.code_array(key) == code

    @params(param_set_code)
    def test_delete_cell(self, key, code, result):
        """Unit test for delete_cell"""

        self.grid.actions.set_code(key, code)
        self.grid.actions.delete_cell(key)

        assert self.grid.code_array(key) is None

    param_get_reference = [
        {'cursor': (0, 0, 0), 'ref_key': (0, 0, 0), 'abs_ref': "S[0, 0, 0]",
         'rel_ref': "S[X, Y, Z]"},
        {'cursor': (0, 0, 1), 'ref_key': (0, 0, 1), 'abs_ref': "S[0, 0, 1]",
         'rel_ref': "S[X, Y, Z]"},
        {'cursor': (0, 0, 0), 'ref_key': (0, 0, 1), 'abs_ref': "S[0, 0, 1]",
         'rel_ref': "S[X, Y, Z+1]"},
        {'cursor': (9, 0, 0), 'ref_key': (0, 0, 0), 'abs_ref': "S[0, 0, 0]",
         'rel_ref': "S[X-9, Y, Z]"},
        {'cursor': (23, 2, 1), 'ref_key': (2, 2, 2), 'abs_ref': "S[2, 2, 2]",
         'rel_ref': "S[X-21, Y, Z+1]"},
    ]

    @params(param_get_reference)
    def test_get_absolute_reference(self, cursor, ref_key, abs_ref, rel_ref):
        """Unit test for _get_absolute_reference"""

        reference = self.grid.actions._get_absolute_reference(ref_key)

        assert reference == abs_ref

    @params(param_get_reference)
    def test_get_relative_reference(self, cursor, ref_key, abs_ref, rel_ref):
        """Unit test for _get_relative_reference"""

        reference = self.grid.actions._get_relative_reference(cursor, ref_key)

        assert reference == rel_ref

    @params(param_get_reference)
    def test_append_reference_code(self, cursor, ref_key, abs_ref, rel_ref):
        """Unit test for append_reference_code"""

        actions = self.grid.actions

        params = [
            # Normal initial code, absolute reference
            {'initial_code': "3 + ", 'ref_type': "absolute",
             "res": actions._get_absolute_reference(ref_key)},
            # Normal initial code, relative reference
            {'initial_code': "3 + ", 'ref_type': "relative",
             "res": actions._get_relative_reference(cursor, ref_key)},
            # Initial code with reference, absolute reference
            {'initial_code': "3 + S[2, 3, 1]", 'ref_type': "absolute",
             "res": actions._get_absolute_reference(ref_key)},
            # Initial code with reference, relative reference
            {'initial_code': "3 + S[2, 3, 1]", 'ref_type': "relative",
             "res": actions._get_relative_reference(cursor, ref_key)},
        ]

        for param in params:
            initial_code = param['initial_code']
            ref_type = param['ref_type']
            res = param['res']

            self.grid.actions.set_code(cursor, initial_code)

            result_code = \
                actions.append_reference_code(cursor, ref_key, ref_type)

            if "S[" in initial_code:
                assert result_code == initial_code[:4] + res

            else:
                assert result_code == initial_code + res

    param_set_cell_attr = [
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 1,
         'attr': ('bordercolor_right', wx.RED), 'testcell': (2, 5, 1)},
        {'selection': Selection([(0, 0)], [(99, 99)], [], [], []), 'tab': 0,
         'attr': ('bordercolor_right', wx.RED), 'testcell': (2, 5, 0)},
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 1,
         'attr': ('bordercolor_bottom', wx.BLUE), 'testcell': (2, 5, 1)},
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 1,
         'attr': ('bgcolor', wx.RED), 'testcell': (2, 5, 1)},
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 2,
         'attr': ('pointsize', 24), 'testcell': (2, 5, 2)},
    ]

    @params(param_set_cell_attr)
    def test_set_cell_attr(self, selection, tab, attr, testcell):
        """Unit test for _set_cell_attr"""

        self.main_window.changed_since_save = False

        attr = {attr[0]: attr[1]}

        self.grid.actions._set_cell_attr(selection, tab, attr)

        color = self.grid.code_array.cell_attributes[testcell][list(attr.keys())[0]]

        assert color == attr[list(attr.keys())[0]]

    def test_set_border_attr(self):
        """Unit test for set_border_attr"""

        self.grid.SelectBlock(10, 10, 20, 20)

        attr = "borderwidth"
        value = 5
        borders = ["top", "inner"]
        tests = {
            (13, 14, 0): 5,
            (53, 14, 0): 1,
        }

        self.grid.actions.set_border_attr(attr, value, borders)
        cell_attributes = self.grid.code_array.cell_attributes

        for cell in tests:
            res = cell_attributes[cell]["borderwidth_bottom"]
            assert res == tests[cell]

    def test_toggle_attr(self):
        """Unit test for toggle_attr"""

        self.grid.SelectBlock(10, 10, 20, 20)

        self.grid.actions.toggle_attr("underline")

        tests = {(13, 14, 0): True, (53, 14, 0): False}

        for cell in tests:
            res = self.grid.code_array.cell_attributes[cell]["underline"]
            assert res == tests[cell]

    param_change_frozen_attr = [
        {'cell': (0, 0, 0), 'code': None, 'result': None},
        {'cell': (0, 0, 0), 'code': "'Test'", 'result': 'Test'},
        {'cell': (2, 2, 0), 'code': "'Test'", 'result': 'Test'},
        {'cell': (2, 1, 0), 'code': "32", 'result': 32},
    ]

    @params(param_change_frozen_attr)
    def test_change_frozen_attr(self, cell, code, result):
        """Unit test for change_frozen_attr"""

        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]
        self.grid.code_array[cell] = code

        self.grid.actions.change_frozen_attr()

        res = self.grid.code_array.frozen_cache[repr(cell)]

        assert res == result

        self.grid.actions.change_frozen_attr()

        res2 = self.grid.code_array.cell_attributes[cell]["frozen"]

        assert not res2

    param_get_new_cell_attr_state = [
        {'cell': (0, 0, 0), 'attr': "fontweight",
         'before': wx.NORMAL, 'next': wx.BOLD},
        {'cell': (2, 1, 0), 'attr': "fontweight",
         'before': wx.NORMAL, 'next': wx.BOLD},
        {'cell': (2, 1, 0), 'attr': "vertical_align",
         'before': "top", 'next': "middle"},
    ]

    @params(param_get_new_cell_attr_state)
    def test_get_new_cell_attr_state(self, cell, attr, before, next):
        """Unit test for get_new_cell_attr_state"""

        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]

        selection = Selection([], [], [], [], [cell[:2]])
        self.grid.actions.set_attr(attr, before, selection)

        res = self.grid.actions.get_new_cell_attr_state(cell, attr)

        assert res == next

    param_get_new_selection_attr_state = [
        {'selection': Selection([], [], [], [], [(0, 0)]), 'cell': (0, 0, 0),
         'attr': "fontweight", 'before': wx.NORMAL, 'next': wx.BOLD},
        {'selection': Selection([], [], [], [], [(2, 1)]), 'cell': (2, 1, 0),
         'attr': "fontweight", 'before': wx.NORMAL, 'next': wx.BOLD},
        {'selection': Selection([], [], [], [], [(2, 1)]), 'cell': (2, 1, 0),
         'attr': "fontweight", 'before': wx.BOLD, 'next': wx.NORMAL},
        {'selection': Selection([], [], [], [], [(2, 1)]), 'cell': (2, 1, 0),
         'attr': "vertical_align", 'before': "top", 'next': "middle"},
        {'selection': Selection([(1, 0)], [(23, 2)], [], [], []),
         'cell': (2, 1, 0),
         'attr': "vertical_align", 'before': "top", 'next': "middle"},
    ]

    @params(param_get_new_selection_attr_state)
    def test_get_new_selection_attr_state(self, cell, selection, attr,
                                          before, next):
        """Unit test for get_new_selection_attr_state"""

        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]

        self.grid.actions.set_attr(attr, before, selection)

        res = self.grid.actions.get_new_selection_attr_state(selection, attr)

        assert res == next

    def test_refresh_selected_frozen_cells(self):
        """Unit test for refresh_selected_frozen_cells"""

        cell = (0, 0, 0)

        code1 = "1"
        code2 = "2"

        self.grid.actions.cursor = cell

        # Fill cell
        self.grid.code_array[cell] = code1

        assert self.grid.code_array[cell] == 1

        # Freeze cell
        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]
        self.grid.actions.change_frozen_attr()

        res = self.grid.code_array.frozen_cache[repr(cell)]
        assert res == eval(code1)

        # Change cell code
        self.grid.code_array[cell] = code2
        assert self.grid.code_array[cell] == 1

        # Refresh cell
        selection = Selection([], [], [], [], [cell[:2]])
        self.grid.actions.refresh_selected_frozen_cells(selection=selection)
        assert self.grid.code_array[cell] == 2

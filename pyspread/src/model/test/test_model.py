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
test_model
==========

Unit tests for model.py

"""

import ast
import fractions  ## Yes, it is required
import math  ## Yes, it is required
import os
import sys

import py.test as pytest
import numpy

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.model.model import KeyValueStore, CellAttributes, DictGrid
from src.model.model import DataArray, CodeArray

from src.lib.selection import Selection

from src.model.unredo import UnRedo


class TestKeyValueStore(object):
    """Unit tests for KeyValueStore"""

    def setup_method(self, method):
        """Creates empty KeyValueStore"""

        self.k_v_store = KeyValueStore()

    def test_missing(self):
        """Test if missing value returns None"""

        key = (1, 2, 3)
        assert self.k_v_store[key] is None

        self.k_v_store[key] = 7

        assert self.k_v_store[key] == 7


class TestCellAttributes(object):
    """Unit tests for CellAttributes"""

    def setup_method(self, method):
        """Creates empty CellAttributes"""

        self.cell_attr = CellAttributes()
        self.cell_attr.unredo = UnRedo()

    def test_undoable_append(self):
        """Test undoable_append"""

        selection = Selection([], [], [], [], [(23, 12)])
        table = 0
        attr = {"angle": 0.2}

        self.cell_attr.undoable_append((selection, table, attr))

        # Check if 2 items - the actual action and the marker - have been added
        assert len(self.cell_attr.unredo.undolist) == 2
        assert len(self.cell_attr.unredo.redolist) == 0
        assert not self.cell_attr._attr_cache

    def test_getitem(self):
        """Test __getitem__"""

        selection_1 = Selection([(2, 2)], [(4, 5)], [55], [55, 66], [(34, 56)])
        selection_2 = Selection([], [], [], [], [(32, 53), (34, 56)])

        self.cell_attr.append((selection_1, 0, {"testattr": 3}))
        self.cell_attr.append((selection_2, 0, {"testattr": 2}))

        assert self.cell_attr[32, 53, 0]["testattr"] == 2
        assert self.cell_attr[2, 2, 0]["testattr"] == 3

    def test_get_merging_cell(self):
        """Test get_merging_cell"""

        selection_1 = Selection([], [], [], [], [(2, 2)])
        selection_2 = Selection([], [], [], [], [(3, 2)])

        self.cell_attr.append((selection_1, 0, {"merge_area": (2, 2, 5, 5)}))
        self.cell_attr.append((selection_2, 0, {"merge_area": (3, 2, 9, 9)}))
        self.cell_attr.append((selection_1, 1, {"merge_area": (2, 2, 9, 9)}))

        # Cell 1. 1, 0 is not merged
        assert self.cell_attr.get_merging_cell((1, 1, 0)) is None

        # Cell 3. 3, 0 is merged to cell 3, 2, 0
        assert self.cell_attr.get_merging_cell((3, 3, 0)) == (3, 2, 0)

        # Cell 2. 2, 0 is merged to cell 2, 2, 0
        assert self.cell_attr.get_merging_cell((2, 2, 0)) == (2, 2, 0)


class TestDictGrid(object):
    """Unit tests for DictGrid"""

    def setup_method(self, method):
        """Creates empty DictGrid"""

        self.dict_grid = DictGrid((100, 100, 100))

    def test_getitem(self):
        """Unit test for __getitem__"""

        with pytest.raises(IndexError):
            self.dict_grid[100, 0, 0]

        self.dict_grid[(2, 4, 5)] = "Test"
        assert self.dict_grid[(2, 4, 5)] == "Test"


class TestDataArray(object):
    """Unit tests for DataArray"""

    def setup_method(self, method):
        """Creates empty DataArray"""

        self.data_array = DataArray((100, 100, 100))

    def test_iter(self):
        """Unit test for __iter__"""

        assert list(iter(self.data_array)) == []

        self.data_array[(1, 2, 3)] = "12"
        self.data_array[(1, 2, 4)] = "13"

        assert sorted(list(iter(self.data_array))) == [(1, 2, 3), (1, 2, 4)]

    def test_keys(self):
        """Unit test for keys"""

        assert list(self.data_array.keys()) == []

        self.data_array[(1, 2, 3)] = "12"
        self.data_array[(1, 2, 4)] = "13"

        assert sorted(self.data_array.keys()) == [(1, 2, 3), (1, 2, 4)]

    def test_pop(self):
        """Unit test for pop"""

        self.data_array[(1, 2, 3)] = "12"
        self.data_array[(1, 2, 4)] = "13"

        assert "12" == self.data_array.pop((1, 2, 3))

        assert sorted(self.data_array.keys()) == [(1, 2, 4)]

    def test_shape(self):
        """Unit test for _get_shape and _set_shape"""

        assert self.data_array.shape == (100, 100, 100)

        self.data_array.shape = (10000, 100, 100)

        assert self.data_array.shape == (10000, 100, 100)

    param_get_last_filled_cell = [
        {'content': {(0, 0, 0): "2"}, 'table': 0, 'res': (0, 0)},
        {'content': {(2, 0, 2): "2"}, 'table': 0, 'res': (0, 0)},
        {'content': {(2, 0, 2): "2"}, 'table': None, 'res': (2, 0)},
        {'content': {(2, 0, 2): "2"}, 'table': 2, 'res': (2, 0)},
        {'content': {(32, 30, 0): "432"}, 'table': 0, 'res': (32, 30)},
    ]

    @params(param_get_last_filled_cell)
    def test_get_last_filled_cell(self, content, table, res):
        """Unit test for get_last_filled_cellet_end"""

        for key in content:
            self.data_array[key] = content[key]

        assert self.data_array.get_last_filled_cell(table)[:2] == res

    def test_getstate(self):
        """Unit test for __getstate__ (pickle support)"""

        assert "dict_grid" in self.data_array.__getstate__()

    def test_slicing(self):
        """Unit test for __getitem__ and __setitem__"""

        self.data_array[0, 0, 0] = "'Test'"
        self.data_array[0, 0, 0] = "'Tes'"

        assert self.data_array[0, 0, 0] == "'Tes'"

    def test_cell_array_generator(self):
        """Unit test for cell_array_generator"""

        cell_array = self.data_array[:5, 0, 0]

        assert list(cell_array) == [None] * 5

        cell_array = self.data_array[:5, :5, 0]

        assert [list(c) for c in cell_array] == [[None] * 5] * 5

        cell_array = self.data_array[:5, :5, :5]

        assert [[list(e) for e in c] for c in cell_array] == \
            [[[None] * 5] * 5] * 5

    def test_set_cell_attributes(self):
        """Unit test for _set_cell_attributes"""

        cell_attributes = ["Test"]
        self.data_array._set_cell_attributes(cell_attributes)
        assert self.data_array.cell_attributes == cell_attributes

    param_adjust_cell_attributes = [
        {'inspoint': 0, 'noins': 5, 'axis': 0,
         'src': (4, 3, 0), 'target': (9, 3, 0)},
        {'inspoint': 34, 'noins': 5, 'axis': 0,
         'src': (4, 3, 0), 'target': (4, 3, 0)},
        {'inspoint': 0, 'noins': 0, 'axis': 0,
         'src': (4, 3, 0), 'target': (4, 3, 0)},
        {'inspoint': 1, 'noins': 5, 'axis': 1,
         'src': (4, 3, 0), 'target': (4, 8, 0)},
        {'inspoint': 1, 'noins': 5, 'axis': 1,
         'src': (4, 3, 1), 'target': (4, 8, 1)},
    ]

    @params(param_adjust_cell_attributes)
    def test_adjust_cell_attributes(self, inspoint, noins, axis, src, target):
        """Unit test for _adjust_cell_attributes"""

        row, col, tab = src

        val = {"angle": 0.2}

        attrs = [(Selection([], [], [], [], [(row, col)]), tab, val)]
        self.data_array._set_cell_attributes(attrs)
        self.data_array._adjust_cell_attributes(inspoint, noins, axis)

        for key in val:
            assert self.data_array.cell_attributes[target][key] == val[key]

    def test_insert(self):
        """Unit test for insert operation"""

        self.data_array[2, 3, 0] = 42
        self.data_array.insert(1, 1, 0)

        assert self.data_array[2, 3, 0] is None

        assert self.data_array[3, 3, 0] == 42

    def test_delete(self):
        """Tests delete operation"""

        self.data_array[2, 3, 4] = "42"
        self.data_array.delete(1, 1, 0)

        assert self.data_array[2, 3, 4] is None
        assert self.data_array[1, 3, 4] == "42"

        try:
            self.data_array.delete(1, 1000, 0)
            assert False
        except ValueError:
            pass

    def test_set_row_height(self):
        """Unit test for set_row_height"""

        self.data_array.set_row_height(7, 1, 22.345)
        assert self.data_array.row_heights[7, 1] == 22.345

    def test_set_col_width(self):
        """Unit test for set_col_width"""

        self.data_array.set_col_width(7, 1, 22.345)
        assert self.data_array.col_widths[7, 1] == 22.345


class TestCodeArray(object):
    """Unit tests for CodeArray"""

    def setup_method(self, method):
        """Creates empty DataArray"""

        self.code_array = CodeArray((100, 10, 3))

    def test_slicing(self):
        """Unit test for __getitem__ and __setitem__"""

        #Test for item getting, slicing, basic evaluation correctness

        shape = self.code_array.shape
        x_list = [0, shape[0]-1]
        y_list = [0, shape[1]-1]
        z_list = [0, shape[2]-1]
        for x, y, z in zip(x_list, y_list, z_list):
            assert self.code_array[x, y, z] is None
            self.code_array[:x, :y, :z]
            self.code_array[:x:2, :y:2, :z:-1]

        get_shape = numpy.array(self.code_array[:, :, :]).shape
        orig_shape = self.code_array.shape
        assert get_shape == orig_shape

        gridsize = 100
        filled_grid = CodeArray((gridsize, 10, 1))
        for i in [-2**99, 2**99, 0]:
            for j in range(gridsize):
                filled_grid[j, 0, 0] = str(i)
                filled_grid[j, 1, 0] = str(i) + '+' + str(j)
                filled_grid[j, 2, 0] = str(i) + '*' + str(j)

            for j in range(gridsize):
                assert filled_grid[j, 0, 0] == i
                assert filled_grid[j, 1, 0] == i + j
                assert filled_grid[j, 2, 0] == i * j

            for j, funcname in enumerate(['int', 'math.ceil',
                                          'fractions.Fraction']):
                filled_grid[0, 0, 0] = "fractions = __import__('fractions')"
                filled_grid[0, 0, 0]
                filled_grid[1, 0, 0] = "math = __import__('math')"
                filled_grid[1, 0, 0]
                filled_grid[j, 3, 0] = funcname + ' (' + str(i) + ')'
                #res = eval(funcname + "(" + "i" + ")")

                assert filled_grid[j, 3, 0] == eval(funcname + "(" + "i" + ")")
        #Test X, Y, Z
        for i in range(10):
            self.code_array[i, 0, 0] = str(i)
        assert [self.code_array((i, 0, 0)) for i in range(10)] == \
            list(map(str, range(10)))

        assert [self.code_array[i, 0, 0] for i in range(10)] == list(range(10))

        # Test cycle detection

        filled_grid[0, 0, 0] = "numpy.arange(0, 10, 0.1)"
        filled_grid[1, 0, 0] = "sum(S[0,0,0])"

        assert filled_grid[1, 0, 0] == sum(numpy.arange(0, 10, 0.1))

        ##filled_grid[0, 0, 0] = "S[5:10, 1, 0]"
        ##assert filled_grid[0, 0, 0].tolist() == range(7, 12)

    def test_make_nested_list(self):
        """Unit test for _make_nested_list"""

        def gen():
            """Nested generator"""

            yield (("Test" for _ in range(2)) for _ in range(2))

        res = self.code_array._make_nested_list(gen())

        assert res == [[["Test" for _ in range(2)] for _ in range(2)]]

    param_get_assignment_target_end = [
        {'code': "a=5", 'res': 1},
        {'code': "a = 5", 'res': 1},
        {'code': "5", 'res': -1},
        {'code': "a == 5", 'res': -1},
        {'code': "", 'res': -1},
        {'code': "fractions = __import__('fractions')", 'res': 9},
        {'code': "math = __import__('math')", 'res': 4},
        {'code': "a = 3==4", 'res': 1},
        {'code': "a == 3 < 44", 'res': -1},
        {'code': "a != 3 < 44", 'res': -1},
        {'code': "a >= 3 < 44", 'res': -1},
        {'code': "a = 3 ; a < 44", 'res': None},
    ]

    @params(param_get_assignment_target_end)
    def test_get_assignment_target_end(self, code, res):
        """Unit test for _get_assignment_target_end"""

        module = ast.parse(code)

        if res is None:
            try:
                self.code_array._get_assignment_target_end(module)
                raise ValueError("Multiple expressions cell not identified")
            except ValueError:
                pass
        else:
            assert self.code_array._get_assignment_target_end(module) == res

    param_eval_cell = [
        {'key': (0, 0, 0), 'code': "2 + 4", 'res': 6},
        {'key': (1, 0, 0), 'code': "S[0, 0, 0]", 'res': None},
        {'key': (43, 2, 1), 'code': "X, Y, Z", 'res': (43, 2, 1)},
    ]

    @params(param_eval_cell)
    def test_eval_cell(self, key, code, res):
        """Unit test for _eval_cell"""

        self.code_array[key] = code
        assert self.code_array._eval_cell(key, code) == res

    def test_execute_macros(self):
        """Unit test for execute_macros"""

        self.code_array.macros = "a = 5\ndef f(x): return x ** 2"
        self.code_array.execute_macros()
        assert self.code_array._eval_cell((0, 0, 0), "a") == 5
        assert self.code_array._eval_cell((0, 0, 0), "f(2)") == 4

    def test_sorted_keys(self):
        """Unit test for _sorted_keys"""

        code_array = self.code_array

        keys = [(1, 0, 0), (2, 0, 0), (0, 1, 0), (0, 99, 0), (0, 0, 0),
                (0, 0, 99), (1, 2, 3)]
        assert list(code_array._sorted_keys(keys, (0, 1, 0))) == \
            [(0, 1, 0), (0, 99, 0), (1, 2, 3), (0, 0, 99), (0, 0, 0),
             (1, 0, 0), (2, 0, 0)]
        sk = list(code_array._sorted_keys(keys, (0, 3, 0), reverse=True))
        assert sk == [(0, 1, 0), (2, 0, 0), (1, 0, 0), (0, 0, 0), (0, 0, 99),
                      (1, 2, 3), (0, 99, 0)]

    def test_string_match(self):
        """Tests creation of string_match"""

        code_array = self.code_array

        test_strings = [
            "", "Hello", " Hello", "Hello ", " Hello ", "Hello\n",
            "THelloT", " HelloT", "THello ", "hello", "HELLO", "sd"
        ]

        search_string = "Hello"

        # Normal search
        flags = []
        results = [None, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, None]
        for test_string, result in zip(test_strings, results):
            res = code_array.string_match(test_string, search_string, flags)
            assert res == result

        flags = ["MATCH_CASE"]
        results = [None, 0, 1, 0, 1, 0, 1, 1, 1, None, None, None]
        for test_string, result in zip(test_strings, results):
            res = code_array.string_match(test_string, search_string, flags)
            assert res == result

        flags = ["WHOLE_WORD"]
        results = [None, 0, 1, 0, 1, 0, None, None, None, 0, 0, None]
        for test_string, result in zip(test_strings, results):
            res = code_array.string_match(test_string, search_string, flags)
            assert res == result

    def test_findnextmatch(self):
        """Find method test"""

        code_array = self.code_array

        for i in range(100):
            code_array[i, 0, 0] = str(i)

        assert code_array[3, 0, 0] == 3
        assert code_array.findnextmatch((0, 0, 0), "3", "DOWN") == (3, 0, 0)
        assert code_array.findnextmatch((0, 0, 0), "99", "DOWN") == (99, 0, 0)

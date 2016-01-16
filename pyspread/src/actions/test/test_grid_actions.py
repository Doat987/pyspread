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
test_grid_actions
=================

Unit tests for _grid_actions.py

"""

import bz2
import os
import sys

try:
    import gnupg
except ImportError:
    gnupg = None

import pytest

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.selection import Selection

from src.lib.testlib import params, pytest_generate_tests
from src.lib.testlib import basic_setup_test, restore_basic_grid

from src.gui._events import *

try:
    from src.lib.gpg import genkey, fingerprint2keyid

except ImportError:
    genkey = None

from src.config import config

from src.lib.testlib import params, pytest_generate_tests


class TestFileActions(object):
    """File actions test class"""

    # Filenames
    # ---------

    # File with valid signature
    filename_valid_sig = TESTPATH + "test1.pys"

    # File without signature
    filename_no_sig = TESTPATH + "test2.pys"

    # File with invalid signature
    filename_invalid_sig = TESTPATH + "test3.pys"

    # File for self.grid size test
    filename_gridsize = TESTPATH + "test4.pys"

    # Empty file
    filename_empty = TESTPATH + "test5.pys"

    # File name that cannot be accessed
    filename_not_permitted = TESTPATH + "test6.pys"

    # File name without file
    filename_wrong = TESTPATH + "test-1.pys"

    # File for testing save
    filename_save = TESTPATH + "test_save.pys"

    def setup_method(self, method):

        # Generate a GPG key if not present
        if fingerprint2keyid(config["gpg_key_fingerprint"]) is None and \
           genkey is not None:
            # No GPG key is configured
            self.fingerprint = genkey(key_name="pyspread_test_key")
        else:
            # Use preconfigured key
            self.fingerprint = config["gpg_key_fingerprint"]

        self.main_window = MainWindow(None, title="pyspread", S=None)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        # Sign files in order to get valid signatures for current key
        self.grid.actions.sign_file(self.filename_valid_sig)
        self.grid.actions.sign_file(self.filename_gridsize)

    def teardown_method(self, method):
        if gnupg is not None and \
           self.fingerprint != config["gpg_key_fingerprint"] and \
           self.fingerprint is not None:
            gpg = gnupg.GPG()
            # Secret key must be deleted first
            gpg.delete_keys(self.fingerprint, True)
            gpg.delete_keys(self.fingerprint)

    param_validate_signature = [
        {'filename': filename_no_sig, 'valid': False},
        {'filename': filename_valid_sig, 'valid': True},
        {'filename': filename_invalid_sig, 'valid': False},
    ]

    @params(param_validate_signature)
    @pytest.mark.skipif(gnupg is None, reason="requires gnupg")
    def test_validate_signature(self, filename, valid):
        """Tests signature validation"""

        assert self.grid.actions.validate_signature(filename) == valid

    def test_enter_safe_mode(self):
        """Tests safe mode entry"""

        self.grid.actions.leave_safe_mode()
        self.grid.actions.enter_safe_mode()
        assert self.grid.code_array.safe_mode

    def test_leave_safe_mode(self):
        """Tests save mode exit"""

        self.grid.actions.enter_safe_mode()
        self.grid.actions.leave_safe_mode()
        assert not self.grid.code_array.safe_mode

    @pytest.mark.skipif(gnupg is None, reason="requires gnupg")
    def test_approve(self):

        # Test if safe_mode is correctly set for invalid sig
        self.grid.actions.approve(self.filename_invalid_sig)

        assert self.grid.GetTable().data_array.safe_mode

        # Test if safe_mode is correctly set for valid sig

        self.grid.actions.approve(self.filename_valid_sig)

        assert not self.grid.GetTable().data_array.safe_mode

        # Test if safe_mode is correctly set for missing sig
        self.grid.actions.approve(self.filename_no_sig)

        assert self.grid.GetTable().data_array.safe_mode

        # Test if safe_mode is correctly set for io-error sig

        os.chmod(self.filename_not_permitted, 0o200)
        os.chmod(self.filename_not_permitted + ".sig", 0o200)

        self.grid.actions.approve(self.filename_not_permitted)

        assert self.grid.GetTable().data_array.safe_mode

        os.chmod(self.filename_not_permitted, 0o644)
        os.chmod(self.filename_not_permitted + ".sig", 0o644)

    def test_clear_globals_reload_modules(self):
        """Tests clear_globals_reload_modules"""

        self.grid.code_array[(0, 0, 0)] = "'Test1'"
        self.grid.code_array[(0, 0, 0)]
        assert self.grid.code_array.result_cache

        self.grid.actions.clear_globals_reload_modules()
        assert not self.grid.code_array.result_cache

    def test_get_file_version(self):
        """Tests infile version string."""

        infile = bz2.BZ2File(self.filename_valid_sig)
        version = self.grid.actions._get_file_version(infile)
        assert version == "0.1"
        infile.close()

    def test_clear(self):
        """Tests empty_grid method"""

        # Set up self.grid

        self.grid.code_array[(0, 0, 0)] = "'Test1'"
        self.grid.code_array[(3, 1, 1)] = "'Test2'"

        self.grid.actions.set_col_width(1, 23)
        self.grid.actions.set_col_width(0, 233)
        self.grid.actions.set_row_height(0, 0)

        selection = Selection([], [], [], [], [(0, 0)])
        self.grid.actions.set_attr("bgcolor", wx.RED, selection)
        self.grid.actions.set_attr("frozen", "print 'Testcode'", selection)

        # Clear self.grid

        self.grid.actions.clear()

        # Code content

        assert self.grid.code_array((0, 0, 0)) is None
        assert self.grid.code_array((3, 1, 1)) is None

        assert list(self.grid.code_array[:2, 0, 0]) == [None, None]

        # Cell attributes
        cell_attributes = self.grid.code_array.cell_attributes
        assert cell_attributes == []

        # Row heights and column widths

        row_heights = self.grid.code_array.row_heights
        assert len(row_heights) == 0

        col_widths = self.grid.code_array.col_widths
        assert len(col_widths) == 0

        # Undo and redo
        undolist = self.grid.code_array.unredo.undolist
        redolist = self.grid.code_array.unredo.redolist
        assert undolist == []
        assert redolist == []

        # Caches

        # Clear self.grid again because lookup is added in resultcache

        self.grid.actions.clear()

        result_cache = self.grid.code_array.result_cache
        assert len(result_cache) == 0

    def test_open(self):
        """Tests open functionality"""

        class Event(object):
            attr = {}
        event = Event()

        # Test missing file
        event.attr["filepath"] = self.filename_wrong

        assert not self.grid.actions.open(event)

        # Test unaccessible file
        os.chmod(self.filename_not_permitted, 0o200)
        event.attr["filepath"] = self.filename_not_permitted
        assert not self.grid.actions.open(event)

        os.chmod(self.filename_not_permitted, 0o644)

        # Test empty file
        event.attr["filepath"] = self.filename_empty
        assert not self.grid.actions.open(event)

        assert self.grid.GetTable().data_array.safe_mode  # sig is also empty

        if gnupg is not None:
            # Test invalid sig files
            event.attr["filepath"] = self.filename_invalid_sig
            self.grid.actions.open(event)

            assert self.grid.GetTable().data_array.safe_mode

            # Test file with sig
            event.attr["filepath"] = self.filename_valid_sig
            self.grid.actions.open(event)

            assert not self.grid.GetTable().data_array.safe_mode

            # Test file without sig
            event.attr["filepath"] = self.filename_no_sig
            self.grid.actions.open(event)

            assert self.grid.GetTable().data_array.safe_mode

            # Test self.grid size for valid file
            event.attr["filepath"] = self.filename_gridsize
            self.grid.actions.open(event)

            new_shape = self.grid.GetTable().data_array.shape
            assert new_shape == (1000, 100, 10)

            # Test self.grid content for valid file
            assert not self.grid.code_array.safe_mode
            assert self.grid.GetTable().data_array[0, 0, 0] == "test4"

    def test_save(self):
        """Tests save functionality"""

        class Event(object):
            attr = {}
        event = Event()

        # Test normal save
        event.attr["filepath"] = self.filename_save

        self.grid.actions.save(event)

        savefile = open(self.filename_save)

        assert savefile
        savefile.close()

        # Test double filename

        self.grid.actions.save(event)

        # Test io error

        os.chmod(self.filename_save, 0o200)
        try:
            self.grid.actions.save(event)
            raise IOError("No error raised even though target not writable")
        except IOError:
            pass
        os.chmod(self.filename_save, 0o644)

        # Test invalid file name

        event.attr["filepath"] = None
        try:
            self.grid.actions.save(event)
            raise TypeError("None accepted as filename")
        except TypeError:
            pass

        if gnupg is not None:
            # Test sig creation is happening

            sigfile = open(self.filename_save + ".sig")
            assert sigfile
            sigfile.close()
            os.remove(self.filename_save + ".sig")

        os.remove(self.filename_save)

    @pytest.mark.skipif(gnupg is None, reason="requires gnupg")
    def test_sign_file(self):
        """Tests signing functionality"""

        try:
            os.remove(self.filename_valid_sig + ".sig")
        except OSError:
            pass
        self.grid.actions.sign_file(self.filename_valid_sig)
        dirlist = os.listdir(TESTPATH)

        filepath = self.filename_valid_sig + ".sig"
        filename = filepath[len(TESTPATH):]

        assert filename in dirlist


class TestTableRowActionsMixins(object):
    """Unit test class for TableRowActionsMixins"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_set_row_height = [
        {'row': 0, 'tab': 0, 'height': 0},
        {'row': 0, 'tab': 1, 'height': 0},
        {'row': 0, 'tab': 0, 'height': 34},
        {'row': 10, 'tab': 12, 'height': 3245.78},
    ]

    @params(param_set_row_height)
    def test_set_row_height(self, row, tab, height):
        self.grid.current_table = tab
        self.grid.actions.set_row_height(row, height)
        row_heights = self.grid.code_array.row_heights
        assert row_heights[row, tab] == height

    param_insert_rows = [
        {'row': -1, 'no_rows': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'row': -1, 'no_rows': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'row': -1, 'no_rows': 1, 'test_key': (1, 0, 0), 'test_val': "'Test'"},
        {'row': -1, 'no_rows': 5, 'test_key': (5, 0, 0), 'test_val': "'Test'"},
        {'row': 1, 'no_rows': 1, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'row': 1, 'no_rows': 1, 'test_key': (1, 0, 0), 'test_val': None},
        {'row': -1, 'no_rows': 1, 'test_key': (2, 1, 0), 'test_val': "3"},
        {'row': 0, 'no_rows': 500, 'test_key': (501, 1, 0), 'test_val': "3"},
    ]

    @params(param_insert_rows)
    def test_insert_rows(self, row, no_rows, test_key, test_val):
        """Tests insertion action for rows"""

        basic_setup_test(self.grid, self.grid.actions.insert_rows, test_key,
                         test_val, row, no_rows=no_rows)

    param_delete_rows = [
        {'row': 0, 'no_rows': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'row': 0, 'no_rows': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'row': 0, 'no_rows': 1, 'test_key': (0, 1, 0), 'test_val': "3"},
        {'row': 0, 'no_rows': 995, 'test_key': (4, 99, 0),
         'test_val': "$^%&$^"},
        {'row': 1, 'no_rows': 1, 'test_key': (0, 1, 0), 'test_val': "1"},
        {'row': 1, 'no_rows': 1, 'test_key': (1, 1, 0), 'test_val': None},
        {'row': 1, 'no_rows': 999, 'test_key': (0, 0, 0),
         'test_val': "'Test'"},
    ]

    @params(param_delete_rows)
    def test_delete_rows(self, row, no_rows, test_key, test_val):
        """Tests deletion action for rows"""

        basic_setup_test(self.grid, self.grid.actions.delete_rows, test_key,
                         test_val, row, no_rows=no_rows)


class TestTableColumnActionsMixin(object):
    """Unit test class for TableColumnActionsMixin"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_set_col_width = [
        {'col': 0, 'tab': 0, 'width': 0},
        {'col': 0, 'tab': 1, 'width': 0},
        {'col': 0, 'tab': 0, 'width': 34},
        {'col': 10, 'tab': 12, 'width': 3245.78},
    ]

    @params(param_set_col_width)
    def test_set_col_width(self, col, tab, width):
        self.grid.current_table = tab
        self.grid.actions.set_col_width(col, width)
        col_widths = self.grid.code_array.col_widths
        assert col_widths[col, tab] == width

    param_set_col_width_selection = [
        {'cursorCol': 1, 'tab': 0, 'width': 7,
         'cols': [0, 1, 2], 'fullboxes': [], 'partialboxes': []},
        {'cursorCol': 1, 'tab': 0, 'width': 8,
         'cols': [], 'fullboxes': [0, 1, 2], 'partialboxes': []},
        {'cursorCol': 1, 'tab': 0, 'width': 9,
         'cols': [], 'fullboxes': [], 'partialboxes': [0, 1, 2]},
        {'cursorCol': 7, 'tab': 0, 'width': 10,
         'cols': [0, 1, 2], 'fullboxes': [], 'partialboxes': []},
        {'cursorCol': 7, 'tab': 0, 'width': 11,
         'cols': [], 'fullboxes': [0, 1, 2], 'partialboxes': []},
        {'cursorCol': 7, 'tab': 0, 'width': 12,
         'cols': [], 'fullboxes': [], 'partialboxes': [0, 1, 2]},
        {'cursorCol': 1, 'tab': 1, 'width': 13,
         'cols': [], 'fullboxes': [], 'partialboxes': []},
        {'cursorCol': 1, 'tab': 1, 'width': 13,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [4, 5]},
        {'cursorCol': 1, 'tab': 1, 'width': 14,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [3, 4]},
        {'cursorCol': 1, 'tab': 1, 'width': 14,
         'cols': [0, 1], 'fullboxes': [1, 2], 'partialboxes': [3, 4]},
        {'cursorCol': 1, 'tab': 1, 'width': 15,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [4, 5]},
        {'cursorCol': 1, 'tab': 1, 'width': 1,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [4, 5]},
    ]

    @params(param_set_col_width_selection)
    def test_set_col_width_selection(self, cursorCol, cols, fullboxes,
                                     partialboxes, tab, width):
        """
        cursorCol: Column user was dragging when trying resize multiple
        cols: Full columns selected to be edited
        fullboxes: Columns which are fully selected via a box in the selection
        partialboxes: Columns which are part of a selection, but do
                    do not include the full columns.
        tab: Current table
        width: Desired new width for all columns
        To run: In this directory !python -m pytest -k test_set_col_width_s
        """
        class event_test_harness(object):
            def __init__(self, cursorCol):
                self.cursorCol = cursorCol

            def GetRowOrCol(self):
                return self.cursorCol

            def Skip(self):
                pass

        # Setup For Test
        max_rows = self.grid.code_array.shape[0] - 1
        event = event_test_harness(cursorCol)
        self.grid.current_table = tab
        self.grid.ClearSelection()
        for col in cols:
            self.grid.SelectCol(col, addToSelected=True)
        for col in fullboxes:
            self.grid.SelectBlock(0, col, max_rows, col, addToSelected=True)
        for col in partialboxes:
            self.grid.SelectBlock(0, col, max_rows-1, col, addToSelected=True)

        # Perform test
        self.grid.actions.set_col_width(cursorCol, width)
        self.grid.handlers.OnColSize(event)

        # Check results -- Cursor col should always be resized
        col_widths = self.grid.code_array.col_widths
        assert col_widths[cursorCol, tab] == width

        # Check results -- Full selected columns
        for col in cols:
            assert col_widths[col, tab] == width

        # Check results -- Boxes of full columns selected
        for col in fullboxes:
            assert col_widths[col, tab] == width

        # Check results -- Boxes of full columns selected
        for col in partialboxes:
            if col != cursorCol and col not in fullboxes:
                assert col_widths.get((col, tab), -1) != width

    param_insert_cols = [
        {'col': -1, 'no_cols': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': "'Test'"},
        {'col': -1, 'no_cols': 5, 'test_key': (0, 5, 0), 'test_val': "'Test'"},
        {'col': 0, 'no_cols': 1, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'col': 0, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': None},
        {'col': 0, 'no_cols': 1, 'test_key': (1, 2, 0), 'test_val': "3"},
    ]

    @params(param_insert_cols)
    def test_insert_cols(self, col, no_cols, test_key, test_val):
        """Tests insertion action for columns"""

        basic_setup_test(self.grid, self.grid.actions.insert_cols, test_key,
                         test_val, col, no_cols=no_cols)

    param_delete_cols = [
        {'col': -1, 'no_cols': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 2, 0), 'test_val': None},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': "2"},
        {'col': -1, 'no_cols': 95, 'test_key': (999, 4, 0),
         'test_val': "$^%&$^"},
        {'col': 0, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': "2"},
        {'col': 0, 'no_cols': 1, 'test_key': (1, 1, 0), 'test_val': "4"},
        {'col': 1, 'no_cols': 99, 'test_key': (0, 0, 0),
         'test_val': "'Test'"},
    ]

    @params(param_delete_cols)
    def test_delete_cols(self, col, no_cols, test_key, test_val):
        """Tests deletion action for columns"""

        basic_setup_test(self.grid, self.grid.actions.delete_cols, test_key,
                         test_val, col, no_cols=no_cols)


class TestTableTabActionsMixin(object):
    """Unit test class for TableTabActionsMixin"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_insert_tabs = [
        {'tab': -1, 'no_tabs': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'tab': -1, 'no_tabs': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'tab': -1, 'no_tabs': 1, 'test_key': (0, 0, 1), 'test_val': "'Test'"},
        {'tab': -1, 'no_tabs': 2, 'test_key': (0, 0, 2), 'test_val': "'Test'"},
        {'tab': 0, 'no_tabs': 1, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'tab': 0, 'no_tabs': 1, 'test_key': (0, 0, 1), 'test_val': None},
    ]

    @params(param_insert_tabs)
    def test_insert_tabs(self, tab, no_tabs, test_key, test_val):
        """Tests insertion action for tabs"""

        basic_setup_test(self.grid, self.grid.actions.insert_tabs, test_key,
                         test_val, tab, no_tabs=no_tabs)

    param_delete_tabs = [
        {'tab': 0, 'no_tabs': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'tab': 0, 'no_tabs': 1, 'test_key': (0, 2, 0), 'test_val': None},
        {'tab': 0, 'no_tabs': 1, 'test_key': (1, 2, 1), 'test_val': "78"},
        {'tab': 2, 'no_tabs': 1, 'test_key': (1, 2, 1), 'test_val': None},
        {'tab': 1, 'no_tabs': 1, 'test_key': (1, 2, 1), 'test_val': "78"},
        {'tab': 0, 'no_tabs': 2, 'test_key': (1, 2, 0), 'test_val': "78"},
    ]

    @params(param_delete_tabs)
    def test_delete_tabs(self, tab, no_tabs, test_key, test_val):
        """Tests deletion action for tabs"""

        basic_setup_test(self.grid, self.grid.actions.delete_tabs, test_key,
                         test_val, tab, no_tabs=no_tabs)


class TestTableActions(object):
    """Unit test class for TableActions"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_paste = [
        {'tl_cell': (0, 0, 0), 'data': [["78"]],
         'test_key': (0, 0, 0), 'test_val': "78"},
        {'tl_cell': (40, 0, 0), 'data': [[None]],
         'test_key': (40, 0, 0), 'test_val': None},
        {'tl_cell': (0, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (0, 0, 0), 'test_val': "1"},
        {'tl_cell': (0, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 1, 0), 'test_val': "4"},
        {'tl_cell': (0, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 1, 1), 'test_val': None},
        {'tl_cell': (41, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (40, 0, 0), 'test_val': None},
        {'tl_cell': (1, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 0, 0), 'test_val': "1"},
        {'tl_cell': (40, 1, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (40, 1, 0), 'test_val': "1"},
        {'tl_cell': (40, 1, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (40, 0, 0), 'test_val': None},
        {'tl_cell': (123, 5, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (123, 6, 0), 'test_val': "2"},
        {'tl_cell': (1, 1, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 1, 2), 'test_val': "1"},
        {'tl_cell': (1, 1, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (2, 1, 2), 'test_val': "3"},
        {'tl_cell': (999, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (999, 0, 0), 'test_val': "1"},
        {'tl_cell': (999, 99, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (999, 99, 2), 'test_val': "1"},
        {'tl_cell': (999, 98, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (999, 99, 2), 'test_val': "2"},
    ]

    @params(param_paste)
    def test_paste(self, tl_cell, data, test_key, test_val):
        """Tests paste into self.grid"""

        basic_setup_test(self.grid, self.grid.actions.paste, test_key,
                         test_val, tl_cell, data)

    param_change_grid_shape = [
        {'shape': (1, 1, 1)},
        {'shape': (2, 1, 3)},
        {'shape': (1, 1, 40)},
        {'shape': (1000, 100, 3)},
        {'shape': (80000000, 80000000, 80000000)},
    ]

    @params(param_change_grid_shape)
    def test_change_grid_shape(self, shape):
        """Tests action for changing the self.grid shape"""

        self.grid.actions.clear()

        self.grid.actions.change_grid_shape(shape)

        res_shape = self.grid.code_array.shape
        assert res_shape == shape

        br_key = tuple(dim - 1 for dim in shape)
        assert self.grid.code_array(br_key) is None

    param_replace_cells = [
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (0, 0, 0), 'res': "3"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (1, 0, 0), 'res': "1"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (2, 0, 0), 'res': "45"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (9, 0, 0), 'res': '33'},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (3, 0, 1), 'res': "1"},
        {'key': (5, 1, 0), 'sorted_row_idxs': [0, 5, 2, 3, 4, 5, 6, 1, 8, 9],
         'res_key': (1, 1, 0), 'res': "3.2"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [0, 5, 2, 3, 4, 5, 6, 1, 8, 9],
         'res_key': (5, 1, 0), 'res': None},
        {'key': (0, 2, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 9, 7, 8, 6],
         'res_key': (9, 2, 0), 'res': "1j"},
    ]

    @params(param_replace_cells)
    def test_replace_cells(self, key, sorted_row_idxs, res_key, res):
        """Tests replace_cells method"""

        self.grid.actions.change_grid_shape((10, 3, 2))

        data = {
            (0, 0, 0): "1",
            (1, 0, 0): "3",
            (2, 0, 0): "45",
            (9, 0, 0): "33",
            (3, 1, 0): "'Test'",
            (5, 1, 0): "3.2",
            (6, 2, 0): "1j",
            (3, 0, 1): "1",
        }
        for __key in data:
            self.grid.code_array[__key] = data[__key]

        self.grid.actions.replace_cells(key, sorted_row_idxs)

        assert self.grid.code_array(res_key) == res

    param_sort_ascending = [
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (0, 0, 0), 'res': "1"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (2, 0, 0), 'res': "33"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (3, 0, 0), 'res': "45"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (4, 0, 0), 'res': None},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (3, 1, 0), 'res': "'Test'"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], [(1, 1)]),
         'res_key': (2, 0, 0), 'res': "45"},
    ]

    @params(param_sort_ascending)
    def test_sort_ascending(self, key, selection, res_key, res):
        """Tests sort_ascending method"""

        self.grid.actions.change_grid_shape((10, 3, 2))

        data = {
            (0, 0, 0): "1",
            (1, 0, 0): "3",
            (2, 0, 0): "45",
            (9, 0, 0): "33",
            (2, 1, 0): "'Test'",
            (5, 1, 0): "3.2",
            (6, 2, 0): "1j",
            (3, 0, 1): "1",
        }

        for __key in data:
            self.grid.code_array[__key] = data[__key]

        selection.grid_select(self.grid)

        try:
            self.grid.actions.sort_ascending(key)
            assert self.grid.code_array(res_key) == res

        except TypeError:
            assert res == 'fail'

    param_sort_descending = [
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (0, 0, 0), 'res': "45"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (2, 0, 0), 'res': "3"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (3, 0, 0), 'res': "1"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (4, 0, 0), 'res': None},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (0, 1, 0), 'res': "'Test'"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], [(1, 1)]),
         'res_key': (2, 0, 0), 'res': "45"},
    ]

    @params(param_sort_descending)
    def test_sort_descending(self, key, selection, res_key, res):
        """Tests sort_descending method"""

        self.grid.actions.change_grid_shape((10, 3, 2))

        data = {
            (0, 0, 0): "1",
            (1, 0, 0): "3",
            (2, 0, 0): "45",
            (9, 0, 0): "33",
            (2, 1, 0): "'Test'",
            (5, 1, 0): "3.2",
            (6, 2, 0): "1j",
            (3, 0, 1): "1",
        }

        for __key in data:
            self.grid.code_array[__key] = data[__key]

        selection.grid_select(self.grid)

        try:
            self.grid.actions.sort_descending(key)
            assert self.grid.code_array(res_key) == res

        except TypeError:
            assert res == 'fail'


class TestUnRedoActions(object):
    """Unit test class for undo and redo actions"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    def test_undo(self):
        """Tests undo action"""

        restore_basic_grid(self.grid)
        self.grid.actions.clear()

        self.grid.code_array[(0, 0, 0)] = "Test"

        self.grid.actions.undo()

        assert self.grid.code_array((0, 0, 0)) is None

    def test_redo(self):
        """Tests redo action"""

        self.test_undo()
        self.grid.actions.redo()

        assert self.grid.code_array((0, 0, 0)) == "Test"


class TestGridActions(object):
    """self.grid level self.grid actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    class Event(object):
        pass

    def test_new(self):
        """Tests creation of a new spreadsheets"""

        dims = [1, 1, 1, 10, 1, 1, 1, 10, 1, 1, 1, 10, 10, 10, 10]
        dims = list(zip(dims[::3], dims[1::3], dims[2::3]))

        for dim in dims:
            event = self.Event()
            event.shape = dim
            self.grid.actions.new(event)
            new_shape = self.grid.GetTable().data_array.shape
            assert new_shape == dim

    param_switch_to_table = [
        {'tab': 2},
        {'tab': 0},
    ]

    @params(param_switch_to_table)
    def test_switch_to_table(self, tab):
        event = self.Event()
        event.newtable = tab
        self.grid.actions.switch_to_table(event)
        assert self.grid.current_table == tab

    param_cursor = [
        {'key': (0, 0, 0)},
        {'key': (0, 1, 2)},
        {'key': (999, 99, 1)},
    ]

    @params(param_cursor)
    def test_cursor(self, key):
        self.grid.cursor = key
        assert self.grid.cursor == key


class TestSelectionActions(object):
    """Selection actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    # No tests for
    # * get_selection
    # * select_cell
    # * select_slice
    # because of close integration with selection in GUI

    def test_delete_selection(self):
        """Tests for delete_selection"""

        self.grid.code_array[(0, 0, 0)] = "Test"
        self.grid.code_array[(0, 0, 1)] = "Not deleted"

        self.grid.actions.select_cell(0, 0)
        self.grid.actions.delete_selection()

        assert self.grid.code_array[(0, 0, 0)] is None
        assert self.grid.code_array((0, 0, 1)) == "Not deleted"

        # Make sure that the result cache is empty
        assert not self.grid.code_array.result_cache

    def test_quote_selection(self):
        """Tests for quote_selection"""

        self.grid.code_array[(1, 0, 0)] = "Q1"
        self.grid.code_array[(2, 0, 0)] = 'u"NQ1"'

        self.grid.actions.select_cell(1, 0)
        self.grid.actions.select_cell(2, 0, add_to_selected=True)

        self.grid.actions.quote_selection()

        assert self.grid.code_array((1, 0, 0)) == 'u"Q1"'
        assert self.grid.code_array((2, 0, 0)) == 'u"NQ1"'


class TestFindActions(object):
    """FindActions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        # Content for find and replace operations
        grid_data = {
            (0, 0, 0): "Test",
            (1, 0, 0): "Test1",
            (2, 0, 0): "Test2",
        }

        for key in grid_data:
            self.grid.code_array[key] = grid_data[key]

    # Search flags ["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]

    param_find = [
        {'gridpos': [0, 0, 0], 'find_string': "test",
         'flags': ["DOWN"], 'res_key': (1, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "test",
         'flags': ["UP"], 'res_key': (2, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "test",
         'flags': ["DOWN", "MATCH_CASE"], 'res_key': None},
        {'gridpos': [1, 0, 0], 'find_string': "test",
         'flags': ["DOWN"], 'res_key': (2, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "Test",
         'flags': ["DOWN", "MATCH_CASE"], 'res_key': (1, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "Test",
         'flags': ["DOWN", "WHOLE_WORD"], 'res_key': (0, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "Test1",
         'flags': ["DOWN", "MATCH_CASE", "WHOLE_WORD"], 'res_key': (1, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "es*.2",
         'flags': ["DOWN"], 'res_key': None},
        {'gridpos': [0, 0, 0], 'find_string': "es*.2",
         'flags': ["DOWN", "REG_EXP"], 'res_key': (2, 0, 0)},
    ]

    @params(param_find)
    def test_find(self, gridpos, find_string, flags, res_key):
        """Tests for find"""

        res = self.grid.actions.find(gridpos, find_string, flags)
        assert res == res_key

    param_replace = [
        {'findpos': (0, 0, 0), 'find_string': "Test",
         'replace_string': "Hello", 'res': "Hello"},
        {'findpos': (1, 0, 0), 'find_string': "Test",
         'replace_string': "Hello", 'res': "Hello1"},
        {'findpos': (1, 0, 0), 'find_string': "est",
         'replace_string': "Hello", 'res': "THello1"},
    ]

    @params(param_replace)
    def test_replace(self, findpos, find_string, replace_string, res):
        """Tests for replace"""

        self.grid.actions.replace(findpos, find_string, replace_string)
        assert self.grid.code_array(findpos) == res


class TestAllGridActions(object):
    """AllGridActions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_replace_bbox_none = [
        {'bbox': ((0, 0), (1, 234)), 'res': ((0, 0), (1, 234))},
        {'bbox': ((None, None), (2, 234)), 'res': ((0, 0), (2, 234))},
        {'bbox': ((None, None), (None, None)), 'res': ((0, 0), (999, 99))},
    ]

    @params(param_replace_bbox_none)
    def test_replace_bbox_none(self, bbox, res):
        """Tests for _replace_bbox_none"""

        assert res == self.grid.actions._replace_bbox_none(bbox)

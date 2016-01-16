#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Jason Sexauer, Martin Manns
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
_grid_cell_editor.py
====================

Provides
--------
 1. GridCellEditor -- Editor displayed when user dobule clicks to edit
    a cell in the grid
"""

import wx
import string

from ._events import post_command_event
from src.gui._widgets import GridEventMixin
from src.lib._string_helpers import quote


class GridCellEditor(wx.grid.PyGridCellEditor, GridEventMixin):
    """In grid cell editor for entering code

    Refer to :
    https://github.com/wxWidgets/wxPython/blob/master/demo/GridCustEditor.py

    """

    def __init__(self, main_window, max_char_width=50):

        self.main_window = main_window
        wx.grid.PyGridCellEditor.__init__(self)

        self.max_char_width = max_char_width
        self.startValue = ""

    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """

        style = wx.TE_MULTILINE
        self._tc = wx.TextCtrl(parent, id, "", style=style)

        # Disable if cell is clocked, enable if cell is not locked
        grid = self.main_window.grid
        key = grid.actions.cursor
        locked = grid.code_array.cell_attributes[key]["locked"] or \
            grid.code_array.cell_attributes[key]["button_cell"]
        self._tc.Enable(not locked)
        self._tc.Show(not locked)

        if locked:
            self._execute_cell_code(key[0], key[1], grid)

        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def SetSize(self, rect):
        """
        Called to position/size the edit control within the cell rectangle.
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.

        """

        grid = self.main_window.grid
        key = grid.actions.cursor

        drawn_rect = grid.grid_renderer._get_drawn_rect(grid, key, rect)

        self._tc.SetDimensions(drawn_rect.x, drawn_rect.y,
                               drawn_rect.width+2, drawn_rect.height+2,
                               wx.SIZE_ALLOW_MINUS_ONE)
        self._tc.Layout()

    def Show(self, show, attr):
        """
        Show or hide the edit control.  You can use the attr (if not None)
        to set colours or fonts for the control.

        """

        super(GridCellEditor, self).Show(show, attr)

    def PaintBackground(self, rect, attr, *args):
        """
        Draws the part of the cell not occupied by the edit control.  The
        base  class version just fills it with background colour from the
        attribute.  In this class the edit control fills the whole cell so
        don't do anything at all in order to reduce flicker.

        """

    def _execute_cell_code(self, row, col, grid):
        """Executes cell code"""

        key = row, col, grid.current_table
        grid.code_array[key]

        grid.ForceRefresh()

    def BeginEdit(self, row, col, grid):
        """
        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*

        """

        # Disable if cell is locked, enable if cell is not locked
        grid = self.main_window.grid
        key = grid.actions.cursor

        locked = grid.code_array.cell_attributes[key]["locked"]or \
            grid.code_array.cell_attributes[key]["button_cell"]
        self._tc.Enable(not locked)
        self._tc.Show(not locked)

        if locked:
            self._execute_cell_code(row, col, grid)

        # Mirror our changes onto the main_window's code bar
        self._tc.Bind(wx.EVT_CHAR, self.OnChar)
        self._tc.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

        # Save cell and grid info
        self._row = row
        self._col = [col, ]  # List of columns we are occupying
        self._grid = grid

        start_value = grid.GetTable().GetValue(*key)

        try:
            start_value_list = [start_value[i:i+self.max_char_width]
                                for i in range(0, len(start_value),
                                                self.max_char_width)]
            startValue = "\n".join(start_value_list)
            self.startValue = startValue

        except TypeError:
            self.startValue = ""

        # Set up the textcontrol to look like this cell (TODO: Does not work)
        try:
            self._tc.SetValue(str(startValue))
        except (TypeError, AttributeError, UnboundLocalError):
            self._tc.SetValue("")

        self._tc.SetFont(grid.GetCellFont(row, col))
        self._tc.SetBackgroundColour(grid.GetCellBackgroundColour(row, col))
        self._update_control_length()

        self._tc.SetInsertionPointEnd()
        self._tc.SetFocus()

        # For this example, select the text
        self._tc.SetSelection(0, self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid, oldVal=None):
        """
        End editing the cell.  This function must check if the current
        value of the editing control is valid and different from the
        original value (available as oldval in its string form.)  If
        it has not changed then simply return None, otherwise return
        the value in its string form.
        *Must Override*

        """

        # Mirror our changes onto the main_window's code bar
        self._tc.Unbind(wx.EVT_KEY_UP)

        self.ApplyEdit(row, col, grid)

        del self._col
        del self._row
        del self._grid

    def ApplyEdit(self, row, col, grid):
        """
        This function should save the value of the control into the
        grid or grid table. It is called only after EndEdit() returns
        a non-None value.
        *Must Override*
        """
        val = self._tc.GetValue()
        grid.GetTable().SetValue(row, col, val)  # update the table

        self.startValue = ''
        self._tc.SetValue('')

    def Reset(self):
        """
        Reset the value in the control back to its starting value.
        *Must Override*
        """

        try:
            self._tc.SetValue(self.startValue)
        except TypeError:
            # Start value was None
            pass
        self._tc.SetInsertionPointEnd()
        # Update the Entry Line
        post_command_event(self.main_window, self.TableChangedMsg,
                           updated_cell=self.startValue)

    def IsAcceptedKey(self, evt):
        """
        Return True to allow the given key to start editing: the base class
        version only checks that the event has no modifiers.  F2 is special
        and will always start the editor.

        """

        ## We can ask the base class to do it
        #return super(MyCellEditor, self).IsAcceptedKey(evt)

        # or do it ourselves

        accepted = super(GridCellEditor, self).IsAcceptedKey(evt)
        accepted = accepted and not evt.ControlDown()
        accepted = accepted and not evt.AltDown()
        accepted = accepted and (evt.GetKeyCode() != wx.WXK_SHIFT)

        return accepted

    def StartingKey(self, evt):
        """
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.
        """

        key = evt.GetKeyCode()
        ch = None
        if key in [
                wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3,
                wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7,
                wx.WXK_NUMPAD8, wx.WXK_NUMPAD9]:

            ch = ch = chr(ord('0') + key - wx.WXK_NUMPAD0)

        elif key < 256 and key >= 0 and chr(key) in string.printable:
            ch = chr(key)

        if ch is not None and self._tc.IsEnabled():
            # For this example, replace the text.  Normally we would append it.
            #self._tc.AppendText(ch)
            self._tc.SetValue(ch)
            self._tc.SetInsertionPointEnd()
        else:
            evt.Skip()

    def StartingClick(self):
        """
        If the editor is enabled by clicking on the cell, this method will be
        called to allow the editor to simulate the click on the control if
        needed.

        """

    def Destroy(self):
        """final cleanup"""

        super(GridCellEditor, self).Destroy()

    def Clone(self):
        """
        Create a new object which is the copy of this one
        *Must Override*

        """

        return GridCellEditor()

    def OnChar(self, event):
        self._update_control_length()
        val = self._tc.GetValue()
        post_command_event(self.main_window, self.TableChangedMsg,
                           updated_cell=val)
        event.Skip()

    def OnKeyUp(self, event):
        # Handle <Ctrl> + <Enter>
        keycode = event.GetKeyCode()
        if keycode == 13 and event.ControlDown():
            self._tc.SetValue(quote(self._tc.GetValue()))
        event.Skip()

    def _update_control_length(self):
        val = self._tc.GetValue()
        extent = self._tc.GetTextExtent(val)[0] + 15  # Small margin
        width, height = self._tc.GetSizeTuple()
        new_width = None
        while width < extent:
            # We need to reszie into the next cell's column
            next_col = self._col[-1] + 1
            try:
                next_col_width = self._grid.GetColSize(next_col)
            except:
                # No nex col because grid is on its right border
                next_col_width = self._grid.GetColSize(self._col[0])

            new_width = width + next_col_width

            self._col.append(next_col)

            width = new_width

        if new_width:
            pos = self._tc.GetPosition()
            self.SetSize(wx.Rect(pos[0], pos[1], new_width-2, height-2))

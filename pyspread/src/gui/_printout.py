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
_printout.py
============

Printout handling module

"""

import math

import wx
import wx.lib.wxcairo

import src.lib.i18n as i18n

from src.lib._grid_cairo_renderer import GridCairoRenderer

from gettext import gettext as _


class Printout(wx.Printout):
    def __init__(self, grid, print_data, print_info):
        start_keys = ["top_row", "left_col", "first_tab"]
        end_keys = ["bottom_row", "right_col", "last_tab"]

        for key in print_info:
            if key == "first_tab":
                value = max(1, int(print_info[key]) + 1)

            elif key in start_keys:
                value = max(0, int(print_info[key]))

            elif key in end_keys:
                idx = end_keys.index(key)
                value = min(grid.code_array.shape[idx],
                            int(print_info[key]) + 1)

            setattr(self, key, value)

        self.grid = grid

        self.print_data = print_data

        if self.print_data.GetOrientation() == wx.LANDSCAPE:
            self.orientation = "landscape"
        else:
            self.orientation = "portrait"

        self.orientation_reversed = self.print_data.IsOrientationReversed()

        wx.Printout.__init__(self)

    def HasPage(self, page):
        """Returns True if the specified page exists.

        Parameters
        ----------
        page: Integer
        \tNumber of page that is checked

        """

        return self.first_tab <= page <= self.last_tab

    def GetPageInfo(self):
        """Returns page information

        What is the page range available, and what is the selected page range.

        """

        return self.first_tab, self.last_tab, self.first_tab, self.last_tab

    def OnPrintPage(self, page):
        dc = self.GetDC()
        width, height = dc.GetSizeTuple()
        mdc = wx.MemoryDC()

        bmp = wx.EmptyBitmap(width, height)
        mdc.SelectObject(bmp)
        mdc.SetBackgroundMode(wx.SOLID)
        mdc.SetBrush(wx.Brush(colour=wx.Colour(255, 255, 255)))
        mdc.SetPen(wx.Pen(colour=wx.Colour(255, 255, 255)))
        mdc.DrawRectangle(0, 0, width, height)
        mdc.SetDeviceOrigin(0, 0)

        # ------------------------------------------
        context = wx.lib.wxcairo.ContextFromDC(mdc)
        code_array = self.grid.code_array

        # Rotate if orientation is reversed
        if self.orientation_reversed:
            context.save()
            context.rotate(math.pi)
            context.translate(-width, -height)

        x_offset = 20.5 * dc.GetPPI()[0] / 96.0
        y_offset = 20.5 * dc.GetPPI()[1] / 96.0

        # Draw cells
        cell_renderer = GridCairoRenderer(context, code_array,
                                          (self.top_row, self.bottom_row),
                                          (self.left_col, self.right_col),
                                          (page - 1, page),
                                          width, height,
                                          self.orientation,
                                          x_offset=x_offset,
                                          y_offset=y_offset,
                                          view_frozen=self.grid._view_frozen)

        mdc.BeginDrawing()

        cell_renderer.draw()

        # Rotate back if orientation is reversed
        if self.orientation_reversed:
            context.restore()

        context.show_page()

        mdc.EndDrawing()

        dc.Blit(0, 0, width, height, mdc, 0, 0, wx.COPY)

        return True

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
clipboard
=========

Provides
--------

 * Clipboard: Clipboard interface class

"""

import wx

import src.lib.i18n as i18n

from gettext import gettext as _


class Clipboard(object):
    """Clipboard access

    Provides:
    ---------
    get_clipboard: Get clipboard content
    set_clipboard: Set clipboard content
    grid_paste: Inserts data into grid target

    """

    clipboard = wx.TheClipboard

    def _convert_clipboard(self, datastring=None, sep='\t'):
        """Converts data string to iterable.

        Parameters:
        -----------
        datastring: string, defaults to None
        \tThe data string to be converted.
        \tself.get_clipboard() is called if set to None
        sep: string
        \tSeparator for columns in datastring

        """

        if datastring is None:
            datastring = self.get_clipboard()

        data_it = ((ele for ele in line.split(sep))
                            for line in datastring.splitlines())
        return data_it

    def get_clipboard(self):
        """Returns the clipboard content

        If a bitmap is contained then it is returned.
        Otherwise, the clipboard text is returned.

        """

        bmpdata = wx.BitmapDataObject()
        textdata = wx.TextDataObject()

        if self.clipboard.Open():
            is_bmp_present = self.clipboard.GetData(bmpdata)
            self.clipboard.GetData(textdata)
            self.clipboard.Close()
        else:
            wx.MessageBox(_("Can't open the clipboard"), _("Error"))

        if is_bmp_present:
            return bmpdata.GetBitmap()
        else:
            return textdata.GetText()

    def set_clipboard(self, data, datatype="text"):
        """Writes data to the clipboard

        Parameters
        ----------
        data: Object
        \tData object for clipboard
        datatype: String in ["text", "bitmap"]
        \tIdentifies datatype to be copied to teh clipboard

        """

        error_log = []

        if datatype == "text":
            data = wx.TextDataObject(text=data)

        elif datatype == "bitmap":
            data = wx.BitmapDataObject(bitmap=data)

        else:
            msg = _("Datatype {type} unknown").format(type=datatype)
            raise ValueError(msg)

        if self.clipboard.Open():
            self.clipboard.SetData(data)
            self.clipboard.Close()
        else:
            wx.MessageBox(_("Can't open the clipboard"), _("Error"))

        return error_log

# end of class Clipboard

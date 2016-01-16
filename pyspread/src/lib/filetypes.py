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

filetypes
=========

This module provides OrderedDict classes with filetype lists and wildcards for
wx.FileDialog.  There are classes for open, save, import, export, macro load
and macro save actions.

The wildcards have to be concatenates with '|' so that it can be used
by wx.FileDialog.


Provides
--------

 * Filetype2WildcardBase: Filetypes to wildcards base class
 * Filetype2Wildcard4Open: Filetypes to wildcards for File->Open
 * Filetype2Wildcard4Save: Filetypes to wildcards for File->SaveAs
 * Filetype2Wildcard4Import: Filetypes to wildcards for File->Import
 * Filetype2Wildcard4Export: Filetypes to wildcards for File->Export
 * Filetype2Wildcard4ExportPDF: Filetypes to wildcards for ExportPDF

"""


from collections import OrderedDict

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import xlwt
except ImportError:
    xlwt = None

try:
    import cairo
except ImportError:
    cairo = None

import src.lib.i18n as i18n
# use ugettext instead of gettext to avoid unicode errors
_ = i18n.language.ugettext


FILETYPE2WILDCARD = {
    # Open and save types
    "pys": _("Pyspread file") + " (*.pys)|*.pys",
    "pysu": _("Uncompressed pyspread file") + " (*.pysu)|*.pysu",
    "xls": _("Excel file") + " (*.xls)|*.xls",
    "xlsx": _("Excel file") + " (*.xlsx)|*.xlsx",
    "all": _("All files") + " (*.*)|*.*",
    # Import and export types
    "csv": _("CSV file") + " (*.*)|*.*",
    "txt": _("Tab delimited text file") + " (*.*)|*.*",
    "pdf": _("PDF file") + " (*.pdf)|*.pdf",
    "svg": _("SVG file") + " (*.svg)|*.svg",
    "py": _("Macro file") + " (*.py)|*.py",
}


FILETYPE_AVAILABILITY = {
    "xls": xlrd is not None and xlwt is not None,  # Reading and writing
    "xlsx": xlrd is not None,
    "pdf": cairo is not None,
    "svg": cairo is not None,
}


def get_filetypes2wildcards(filetypes):
    """Returns OrderedDict of filetypes to wildcards

    The filetypes that are provided in the filetypes parameter are checked for
    availability. Only available filetypes are inluded in the return ODict.

    Parameters
    ----------
    filetypes: Iterable of strings
    \tFiletype list

    """

    def is_available(filetype):
        return filetype not in FILETYPE_AVAILABILITY or \
               FILETYPE_AVAILABILITY[filetype]

    available_filetypes = list(filter(is_available, filetypes))

    return OrderedDict((ft, FILETYPE2WILDCARD[ft])
                       for ft in available_filetypes)

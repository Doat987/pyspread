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
icons
=====

Provides:
---------
  1) GtkArtProvider: Provides stock and custom icons
  2) Icons: Provides pyspread's icons

"""

import os

import wx

from src.sysvars import get_program_path


class GtkArtProvider(wx.ArtProvider):
    """Provides extra icons in addition to the standard ones

    Used only by Icons class

    """

    def __init__(self, theme, icon_size):

        wx.ArtProvider.__init__(self)

        theme_path, icon_path, action_path, toggle_path = \
            self.get_paths(theme, icon_size)

        self.extra_icons = {
            "PyspreadLogo": theme_path + "pyspread.png",
            "EditCopyRes": action_path + "edit-copy-results.png",
            "FormatTextBold": action_path + "format-text-bold.png",
            "FormatTextItalic": action_path + "format-text-italic.png",
            "FormatTextUnderline": action_path +
                                            "format-text-underline.png",
            "FormatTextStrikethrough": action_path +
                                            "format-text-strikethrough.png",
            "JustifyRight": action_path + "format-justify-right.png",
            "JustifyCenter": action_path + "format-justify-center.png",
            "JustifyLeft": action_path + "format-justify-left.png",
            "AlignTop": action_path + "format-text-aligntop.png",
            "AlignCenter": action_path + "format-text-aligncenter.png",
            "AlignBottom": action_path + "format-text-alignbottom.png",
            "Freeze": action_path + "frozen_small.png",
            "Lock": action_path + "lock.png",
            "Markup": action_path + "format_text_markup.png",
            "Merge": action_path + "format-merge-table-cells.png",
            "AllBorders": toggle_path + "border_all.xpm",
            "LeftBorders": toggle_path + "border_left.xpm",
            "RightBorders": toggle_path + "border_right.xpm",
            "TopBorders": toggle_path + "border_top.xpm",
            "BottomBorders": toggle_path + "border_bottom.xpm",
            "InsideBorders": toggle_path + "border_inside.xpm",
            "OutsideBorders": toggle_path + "border_outside.xpm",
            "TopBottomBorders": toggle_path + "border_top_n_bottom.xpm",
            "MATCH_CASE": toggle_path + "aA.png",
            "REG_EXP": toggle_path + "regex.png",
            "WHOLE_WORD": toggle_path + "wholeword.png",
            "InsertBitmap": action_path + "insert_bmp.png",
            "LinkBitmap": action_path + "link_bmp.png",
            "InsertChart": action_path + "chart_line.png",
            "plot": action_path + "chart_line.png",  # matplotlib plot chart
            "bar": action_path + "chart_column.png",  # matplotlib bar chart
            "boxplot": action_path + "chart_boxplot.png",  # matplotlib boxplot
            "pie": action_path + "chart_pie.png",  # matplotlib pie chart
            "hist": action_path + "chart_histogram.png",  # matplotlib hist
            "annotate": action_path + "chart_annotate.png",  # matplotlib
            "contour": action_path + "chart_contour.png",  # matplotlib
            "Sankey": action_path + "chart_sankey.png",  # matplotlib
            "safe_mode": icon_path + "status/dialog-warning.png",
            "SortAscending": action_path + "edit-sort-ascending.png",
            "SortDescending": action_path + "edit-sort-descending.png",
            "ExportPDF": action_path + "export_pdf.png",
            "TextRotate0": action_path + "format-text-rotate0.png",
            "TextRotate90": action_path + "format-text-rotate90.png",
            "TextRotate180": action_path + "format-text-rotate180.png",
            "TextRotate270": action_path + "format-text-rotate270.png",
            "BUTTON_CELL": action_path + "button_ok.png",
        }

    def get_paths(self, theme, icon_size):
        """Returns tuple of theme, icon, action and toggle paths"""

        _size_str = "x".join(map(str, icon_size))

        theme_path = get_program_path() + "share" + os.sep + "icons" + os.sep
        icon_path = theme_path + theme + os.sep + _size_str + os.sep
        action_path = icon_path + "actions" + os.sep
        toggle_path = icon_path + "toggles" + os.sep

        return theme_path, icon_path, action_path, toggle_path

    def CreateBitmap(self, artid, client, size):
        """Adds custom images to Artprovider"""

        if artid in self.extra_icons:
            return wx.Bitmap(self.extra_icons[artid], wx.BITMAP_TYPE_ANY)

        else:
            return wx.Bitmap()  #wx.ArtProvider.GetBitmap(artid, client, size)


class WindowsArtProvider(GtkArtProvider):
    """Provides extra icons for the Windows platform"""

    def __init__(self, theme, icon_size):
        GtkArtProvider.__init__(self, theme, icon_size)

        theme_path, icon_path, action_path, toggle_path = \
            self.get_paths(theme, icon_size)

        windows_icons = {
            wx.ART_NEW: action_path + "document-new.png",
            wx.ART_FILE_OPEN: action_path + "document-open.png",
            wx.ART_FILE_SAVE: action_path + "document-save.png",
            wx.ART_FILE_SAVE_AS: action_path + "document-save-as.png",
            wx.ART_PRINT: action_path + "document-print.png",
            wx.ART_GO_UP: action_path + "go-up.png",
            wx.ART_GO_DOWN: action_path + "go-down.png",
            wx.ART_COPY: action_path + "edit-copy.png",
            wx.ART_CUT: action_path + "edit-cut.png",
            wx.ART_PASTE: action_path + "edit-paste.png",
            wx.ART_UNDO: action_path + "edit-undo.png",
            wx.ART_REDO: action_path + "edit-redo.png",
            wx.ART_FIND: action_path + "edit-find.png",
            wx.ART_FIND_AND_REPLACE: action_path + "edit-find-replace.png",

        }

        self.extra_icons.update(windows_icons)


class Icons(object):
    """Provides icons for pyspread

    Parameters
    ----------
    icon_set: Integer, defaults to wx.ART_OTHER
    \tIcon set as defined by wxArtProvider
    icon_theme: String, defaults to "Tango"
    \tIcon theme
    icon_size: 2-Tuple of Integer, defaults to (24, 24)
    \tI=Size of icon bitmaps

    """

    theme = "Tango"

    icon_size = (24, 24)
    icon_set = wx.ART_OTHER

    icons = {
        "FileNew": wx.ART_NEW,
        "FileOpen": wx.ART_FILE_OPEN,
        "FileSave": wx.ART_FILE_SAVE,
        "FilePrint": wx.ART_PRINT,
        "EditCut": wx.ART_CUT,
        "EditCopy": wx.ART_COPY,
        "EditPaste": wx.ART_PASTE,
        "Undo": wx.ART_UNDO,
        "Redo": wx.ART_REDO,
        "Find": wx.ART_FIND,
        "FindReplace": wx.ART_FIND_AND_REPLACE,
        "GoUp": wx.ART_GO_UP,
        "GoDown": wx.ART_GO_DOWN,
        "Add": wx.ART_ADD_BOOKMARK,
        "Remove": wx.ART_DEL_BOOKMARK,
    }

    def __init__(self, icon_set=wx.ART_OTHER, icon_theme="Tango",
                 icon_size=(24, 24)):

        self.icon_set = icon_set
        self.icon_theme = icon_theme
        self.icon_size = icon_size

        if "__WXMSW__" in wx.PlatformInfo:
            # Windows lacks good quality stock items
            wx.ArtProvider.Push(WindowsArtProvider(icon_theme, icon_size))
        else:
            # Use the platform generic themed icons instead
            wx.ArtProvider.Push(GtkArtProvider(icon_theme, icon_size))

    def __getitem__(self, icon_name):
        """Returns by bitmap

        Parameters
        ----------
        icon_name: String
        \tString identifier of the icon.

        """

        if icon_name in self.icons:
            icon_name = self.icons[icon_name]

        return wx.ArtProvider.GetBitmap(icon_name, self.icon_set,
                                        self.icon_size)

icons = Icons()

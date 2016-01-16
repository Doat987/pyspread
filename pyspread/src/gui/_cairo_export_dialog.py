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
_pdf_export_dialog
==================

Provides:
---------
  1) CairoExportDialog

"""

import wx
from wx.lib.intctrl import IntCtrl
from collections import OrderedDict
import src.lib.i18n as i18n
_ = i18n.language.ugettext


class CairoExportDialog(wx.Dialog):
    """Gets Cairo export parameters from user"""

    # 72 points = 1 inch

    paper_sizes_points = OrderedDict([
        ("A4", (595, 842)),
        ("Letter", (612, 792)),
        ("Tabloid", (792, 1224)),
        ("Ledger", (1224, 792)),
        ("Legal", (612, 1008)),
        ("Statement", (396, 612)),
        ("Executive", (540, 720)),
        ("A0", (2384, 3371)),
        ("A1", (1685, 2384)),
        ("A2", (1190, 1684)),
        ("A3", (842, 1190)),
        ("A4Small", (595, 842)),
        ("A5", (420, 595)),
        ("B4", (729, 1032)),
        ("B5", (516, 729)),
        ("Folio", (612, 936)),
        ("Quarto", (610, 780)),
        ("10x14", (720, 1008)),
        ])

    def __init__(self, parent, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        try:
            self.filetype = kwds.pop("filetype").lower()
        except KeyError:
            self.filetype = "pdf"

        self.parent = parent
        wx.Dialog.__init__(self, parent, *args, **kwds)

        if self.filetype != "print":
            # If printing and not exporting then page info is
            # gathered from printer dialog

            self.portrait_landscape_radio_box = \
                wx.RadioBox(self, wx.ID_ANY, _("Layout"),
                            choices=[_("Portrait"), _("Landscape")],
                            majorDimension=2,
                            style=wx.RA_SPECIFY_COLS)
            self.page_width_label = wx.StaticText(self, wx.ID_ANY, _("Width"))
            self.page_width_text_ctrl = wx.TextCtrl(self, wx.ID_ANY)
            self.page_height_label = wx.StaticText(self, wx.ID_ANY,
                                                   _("Height"))
            self.page_height_text_ctrl = wx.TextCtrl(self, wx.ID_ANY)
            self.page_layout_choice = \
                wx.Choice(self, wx.ID_ANY,
                          choices=list(self.paper_sizes_points.keys()))
            self.sizer_2_staticbox = wx.StaticBox(self, wx.ID_ANY, _("Page"))

            self.page_layout_choice.Bind(wx.EVT_CHOICE,
                                         self.on_page_layout_choice)

        self.top_row_label = wx.StaticText(self, wx.ID_ANY, _("Top row"))
        self.top_row_text_ctrl = IntCtrl(self, wx.ID_ANY)
        self.bottom_row_label = wx.StaticText(self, wx.ID_ANY, _("Bottom row"))
        self.bottom_row_text_ctrl = IntCtrl(self, wx.ID_ANY)
        self.left_col_label = wx.StaticText(self, wx.ID_ANY, _("Left column"))
        self.left_col_text_ctrl = IntCtrl(self, wx.ID_ANY)
        self.right_col_label = wx.StaticText(self, wx.ID_ANY,
                                             _("Right column"))
        self.right_col_text_ctrl = IntCtrl(self, wx.ID_ANY)
        self.first_tab_label = wx.StaticText(self, wx.ID_ANY, _("First table"))
        self.first_tab_text_ctrl = IntCtrl(self, wx.ID_ANY)
        self.last_tab_label = wx.StaticText(self, wx.ID_ANY, _("Last table"))
        self.last_tab_text_ctrl = IntCtrl(self, wx.ID_ANY)
        self.sizer_3_staticbox = wx.StaticBox(self, wx.ID_ANY, _("Grid"))
        self.empty_panel = wx.Panel(self, wx.ID_ANY)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, "")
        self.ok_button = wx.Button(self, wx.ID_OK, "")

        self.__set_properties()
        self.__do_layout()

    def _get_dialog_title(self):
        """Returns title string"""

        title_filetype = self.filetype[0].upper() + self.filetype[1:]

        if self.filetype == "print":
            title_export = ""
        else:
            title_export = " export"

        return _("{filetype}{export} options").format(filetype=title_filetype,
                                                      export=title_export)

    def __set_properties(self):

        (top, left), (bottom, right) = \
            self.parent.grid.actions.get_visible_area()

        self.SetTitle(self._get_dialog_title())

        if self.filetype != "print":
            # If printing and not exporting then page info is
            # gathered from printer dialog
            self.portrait_landscape_radio_box.SetToolTipString(
                _("Choose portrait or landscape page layout"))
            self.portrait_landscape_radio_box.SetSelection(0)
            self.page_width_label.SetToolTipString(_("Page width in inches"))
            self.page_width_text_ctrl.SetToolTipString(
                _("Page width in inches"))
            self.page_width_text_ctrl.SetValue(
                str(self.paper_sizes_points["A4"][0] / 72.0))
            self.page_height_label.SetToolTipString(_("Page height in inches"))
            self.page_height_text_ctrl.SetToolTipString(
                _("Page height in inches"))
            self.page_height_text_ctrl.SetValue(
                str(self.paper_sizes_points["A4"][1] / 72.0))
            self.page_layout_choice.SetToolTipString(
                _("Choose from predefined page layouts"))
            self.page_layout_choice.SetSelection(0)

        self.top_row_label.SetToolTipString(_("Top row to be exported"))
        self.top_row_text_ctrl.SetToolTipString(_("Top row to be exported"))
        self.top_row_text_ctrl.SetValue(top)
        self.bottom_row_label.SetToolTipString(_("Bottom row to be exported"))
        self.bottom_row_text_ctrl.SetToolTipString(
            _("Bottom row to be exported"))
        self.bottom_row_text_ctrl.SetValue(bottom)
        self.left_col_label.SetToolTipString(
            _("Leftmost column to be exported"))
        self.left_col_text_ctrl.SetToolTipString(
            _("Left column to be exported"))
        self.left_col_text_ctrl.SetValue(left)
        self.right_col_label.SetToolTipString(
            _("Rightmost column to be exported"))
        self.right_col_text_ctrl.SetToolTipString(
            _("Right column to be exported"))
        self.right_col_text_ctrl.SetValue(right)
        self.first_tab_label.SetToolTipString(_("First table to be exported"))
        self.first_tab_text_ctrl.SetToolTipString(
            _("First table to be exported"))
        self.first_tab_text_ctrl.SetValue(self.parent.grid.current_table)
        self.last_tab_label.SetToolTipString(_("Last table to be exported"))
        self.last_tab_text_ctrl.SetToolTipString(
            _("Last table to be exported"))
        self.last_tab_text_ctrl.SetValue(self.parent.grid.current_table)

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_1 = wx.FlexGridSizer(3, 1, 0, 0)
        grid_sizer_2 = wx.FlexGridSizer(1, 3, 0, 0)
        self.sizer_3_staticbox.Lower()
        sizer_3 = wx.StaticBoxSizer(self.sizer_3_staticbox, wx.HORIZONTAL)
        grid_sizer_4 = wx.FlexGridSizer(3, 4, 0, 0)

        if self.filetype != "print":
            # If printing and not exporting then page info is
            # gathered from printer dialog
            self.sizer_2_staticbox.Lower()
            sizer_2 = wx.StaticBoxSizer(self.sizer_2_staticbox, wx.VERTICAL)
            grid_sizer_3 = wx.FlexGridSizer(1, 5, 0, 0)
            sizer_2.Add(self.portrait_landscape_radio_box, 0,
                        wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL, 3)
            grid_sizer_3.Add(self.page_width_label, 0,
                             wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
            grid_sizer_3.Add(self.page_width_text_ctrl, 0,
                             wx.ALL | wx.EXPAND, 3)
            grid_sizer_3.Add(self.page_height_label, 0,
                             wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
            grid_sizer_3.Add(self.page_height_text_ctrl, 0,
                             wx.ALL | wx.EXPAND, 3)
            grid_sizer_3.Add(self.page_layout_choice, 0, wx.ALL | wx.EXPAND, 3)
            grid_sizer_3.AddGrowableCol(1)
            grid_sizer_3.AddGrowableCol(3)
            grid_sizer_3.AddGrowableCol(4)
            sizer_2.Add(grid_sizer_3, 3, wx.ALL | wx.EXPAND, 3)
            grid_sizer_1.Add(sizer_2, 1, wx.ALL | wx.EXPAND, 3)

        grid_sizer_4.Add(self.top_row_label, 0,
                         wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        grid_sizer_4.Add(self.top_row_text_ctrl, 0, wx.ALL | wx.EXPAND, 3)
        grid_sizer_4.Add(self.bottom_row_label, 0,
                         wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        grid_sizer_4.Add(self.bottom_row_text_ctrl, 0, wx.ALL | wx.EXPAND, 3)
        grid_sizer_4.Add(self.left_col_label, 0, wx.ALL, 3)
        grid_sizer_4.Add(self.left_col_text_ctrl, 0, wx.ALL | wx.EXPAND, 3)
        grid_sizer_4.Add(self.right_col_label, 0, wx.ALL, 3)
        grid_sizer_4.Add(self.right_col_text_ctrl, 0, wx.ALL | wx.EXPAND, 3)
        grid_sizer_4.Add(self.first_tab_label, 0, wx.ALL, 3)
        grid_sizer_4.Add(self.first_tab_text_ctrl, 0, wx.ALL | wx.EXPAND, 3)
        grid_sizer_4.Add(self.last_tab_label, 0,
                         wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        grid_sizer_4.Add(self.last_tab_text_ctrl, 0, wx.ALL | wx.EXPAND, 3)
        grid_sizer_4.AddGrowableCol(1)
        grid_sizer_4.AddGrowableCol(3)
        sizer_3.Add(grid_sizer_4, 1, wx.ALL | wx.EXPAND, 3)
        grid_sizer_1.Add(sizer_3, 1, wx.ALL | wx.EXPAND, 3)
        grid_sizer_2.Add(self.empty_panel, 1, wx.ALL | wx.EXPAND, 3)
        grid_sizer_2.Add(self.cancel_button, 0, wx.ALL, 3)
        grid_sizer_2.Add(self.ok_button, 0, wx.ALL, 3)
        grid_sizer_2.AddGrowableRow(0)
        grid_sizer_2.AddGrowableCol(0)
        grid_sizer_1.Add(grid_sizer_2, 1, wx.ALL | wx.EXPAND, 3)
        grid_sizer_1.AddGrowableRow(0)
        grid_sizer_1.AddGrowableRow(1)
        grid_sizer_1.AddGrowableCol(0)
        sizer_1.Add(grid_sizer_1, 1, wx.ALL | wx.EXPAND, 3)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def on_page_layout_choice(self, event):
        """Page layout choice event handler"""

        width, height = self.paper_sizes_points[event.GetString()]
        self.page_width_text_ctrl.SetValue(str(width / 72.0))
        self.page_height_text_ctrl.SetValue(str(height / 72.0))

        event.Skip()

    def get_info(self):
        """Returns a dict with the dialog PDF info

        Dict keys are:
        top_row, bottom_row, left_col, right_col, first_tab, last_tab,
        paper_width, paper_height

        """

        info = {}

        info["top_row"] = self.top_row_text_ctrl.GetValue()
        info["bottom_row"] = self.bottom_row_text_ctrl.GetValue()
        info["left_col"] = self.left_col_text_ctrl.GetValue()
        info["right_col"] = self.right_col_text_ctrl.GetValue()
        info["first_tab"] = self.first_tab_text_ctrl.GetValue()
        info["last_tab"] = self.last_tab_text_ctrl.GetValue()

        if self.filetype != "print":
            # If printing and not exporting then page info is
            # gathered from printer dialog

            info["paper_width"] = float(
                self.page_width_text_ctrl.GetValue()) * 72.0
            info["paper_height"] = float(
                self.page_height_text_ctrl.GetValue()) * 72.0

            if self.portrait_landscape_radio_box.GetSelection() == 0:
                orientation = "portrait"
            elif self.portrait_landscape_radio_box.GetSelection() == 1:
                orientation = "landscape"
            else:
                raise ValueError("Orientation not in portrait or landscape")

            info["orientation"] = orientation

        return info

# end of class PdfExportDialog\

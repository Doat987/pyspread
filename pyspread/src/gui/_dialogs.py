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
_dialogs
========

Provides:
---------
  - ChoiceRenderer: Renders choice dialog box for grid
  - CsvParameterWidgets: CSV parameter entry panel content
  - CSVPreviewGrid: Grid in CSV import parameter entry panel
  - CSVPreviewTextCtrl: TextCtrl in CSV export parameter entry panel
  - CsvImportDialog: Dialog for CSV import parameter choice
  - CsvExportDialog:  Dialog for CSV export parameter choice
  - MacroDialog: Dialog for macro management
  - DimensionsEntryDialog
  - CellEntryDialog
  - AboutDialog
  - PreferencesDialog
  - GPGParamsDialog
  - PasteAsDialog

"""

import io
import csv
import os
import string
import types

import wx
import wx.grid
from wx.lib.wordwrap import wordwrap
import wx.lib.masked
import wx.stc as stc

from src.config import config, VERSION
from src.sysvars import get_program_path
from src.gui._widgets import PythonSTC
from src.gui._events import post_command_event
from src.gui._events import MainWindowEventMixin, GridEventMixin
from src.lib.__csv import Digest, sniff, get_first_line, encode_gen
from src.lib.__csv import csv_digest_gen, cell_key_val_gen
from src.lib.exception_handling import get_user_codeframe

import ast
from traceback import print_exception
from io import StringIO
from sys import exc_info
from gettext import gettext as _


class IntValidator(wx.PyValidator):
    """IntTextCtrl input validation class"""

    def __init__(self):
        wx.PyValidator.__init__(self)\

        self.Bind(wx.EVT_CHAR, self.OnChar)

    def TransferToWindow(self):
            return True

    def TransferFromWindow(self):
            return True

    def Clone(self):
        return wx.Validator()

    def Validate(self, win):
        """Returns True if Value in digits, False otherwise"""

        val = self.GetWindow().GetValue()

        for x in val:
            if x not in string.digits:
                return False

        return True

    def OnChar(self, event):
        """Eats event if key not in digits"""

        key = event.GetKeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255 or \
           chr(key) in string.digits:
            event.Skip()

        # Returning without calling even.Skip eats the event
        #  before it gets to the text control


# end of class IntValidator

class ChoiceRenderer(wx.grid.PyGridCellRenderer):
    """Renders choice dialog box for grid

    Places an image in a cell based on the row index.
    There are N choices and the choice is made by  choice[row%N]

    """

    def __init__(self, table):

        wx.grid.PyGridCellRenderer.__init__(self)
        self.table = table

        self.iconwidth = 32

    def Draw(self, grid, attr, dc, rect, row, col, is_selected):
        """Draws the text and the combobox icon"""

        render = wx.RendererNative.Get()

        # clear the background
        dc.SetBackgroundMode(wx.SOLID)

        if is_selected:
            dc.SetBrush(wx.Brush(wx.BLUE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.BLUE, 1, wx.SOLID))
        else:
            dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.SOLID))
        dc.DrawRectangleRect(rect)

        cb_lbl = grid.GetCellValue(row, col)
        string_x = rect.x + 2
        string_y = rect.y + 2
        dc.DrawText(cb_lbl, string_x, string_y)

        button_x = rect.x + rect.width - self.iconwidth
        button_y = rect.y
        button_width = self.iconwidth
        button_height = rect.height
        button_size = button_x, button_y, button_width, button_height
        render.DrawComboBoxDropButton(grid, dc, button_size,
                                      wx.CONTROL_CURRENT)


class CsvParameterWidgets(object):
    """
    This class holds the csv parameter entry panel

    It returns a sizer that contains the widgets

    Parameters
    ----------
    parent: wx.Window
    \tWindow at which the widgets will be placed
    csvfilepath: String
    \tPath of csv file

    """

    csv_params = [
        ["encodings", tuple, _("Encoding"),
         _("CSV file encoding.")],
        ["dialects", tuple, _("Dialect"),
         _("To make it easier to specify the format of input and output "
           "records, specific formatting parameters are grouped together "
           "into dialects.\n'excel': Defines the usual properties of an "
           "Excel-generated CSV file.\n'sniffer': Deduces the format of a "
           "CSV file\n'excel-tab': Defines the usual "
           "properties of an Excel-generated TAB-delimited file.")],
        ["delimiter", bytes, _("Delimiter"),
         _("A one-character string used to separate fields.")],
        ["doublequote", bool, _("Doublequote"),
         _("Controls how instances of quotechar appearing inside a "
           "field should be themselves be quoted. When True, the character "
           "is doubled. When False, the escapechar is used as a prefix to "
           "the quotechar.")],
        ["escapechar", bytes, _("Escape character"),
         _("A one-character string used by "
           "the writer to escape the delimiter if quoting is set to "
           "QUOTE_NONE and the quotechar if doublequote is False. On "
           "reading, the escapechar removes any special meaning from the "
           "following character.")],
        ["quotechar", bytes, _("Quote character"),
         _("A one-character string used to quote fields containing special "
           "characters, such as the delimiter or quotechar, or which "
           "contain new-line characters.")],
        ["quoting", int, _("Quoting style"),
         _("Controls when quotes should be recognised.")],
        ["self.has_header", bool, _("Header present"),
         _("Analyze the CSV file and treat the first row as strings if it "
           "appears to be a series of column headers.")],
        ["skipinitialspace", bool, _("Skip initial space"),
         _("When True, whitespace immediately following the delimiter is "
           "ignored.")],
    ]

    type2widget = {
        bytes: wx.TextCtrl,
        bool: wx.CheckBox,
        tuple: wx.Choice,
        int: wx.Choice,
    }

    standard_encodings = (
        "utf-8", "ascii", "big5", "big5hkscs", "cp037", "cp424", "cp437",
        "cp500", "cp720", "cp737", "cp775", "cp850", "cp852", "cp855", "cp856",
        "cp857", "cp858", "cp860", "cp861", "cp862", "cp863", "cp864", "cp865",
        "cp866", "cp869", "cp874", "cp875", "cp932", "cp949", "cp950",
        "cp1006", "cp1026", "cp1140", "cp1250", "cp1251", "cp1252", "cp1253",
        "cp1254", "cp1255", "cp1256", "cp1257", "cp1258", "euc-jp",
        "euc-jis-2004", "euc-jisx0213", "euc-kr", "gb2312", "gbk", "gb18030",
        "hz", "iso2022-jp", "iso2022-jp-1", "iso2022-jp-2", "iso2022-jp-2004",
        "iso2022-jp-3", "iso2022-jp-ext", "iso2022-kr", "latin-1", "iso8859-2",
        "iso8859-3", "iso8859-4", "iso8859-5", "iso8859-6", "iso8859-7",
        "iso8859-8", "iso8859-9", "iso8859-10", "iso8859-13", "iso8859-14",
        "iso8859-15", "iso8859-16", "johab", "koi8-r", "koi8-u",
        "mac-cyrillic", "mac-greek", "mac-iceland", "mac-latin2", "mac-roman",
        "mac-turkish", "ptcp154", "shift-jis", "shift-jis-2004",
        "shift-jisx0213", "utf-32", "utf-32-be", "utf-32-le", "utf-16",
        "utf-16-be", "utf-16-le", "utf-7", "utf-8-sig",
    )

    # All tuple types from csv_params have choice boxes
    choices = {
        'dialects': tuple(["sniffer"] + csv.list_dialects() + ["user"]),
        'quoting': ("QUOTE_ALL", "QUOTE_MINIMAL",
                    "QUOTE_NONNUMERIC", "QUOTE_NONE"),
        'encodings': standard_encodings,
    }

    widget_handlers = {
        'encodings': "OnEncoding",
        'dialects': "OnDialectChoice",
        'quoting': "OnWidget",
        'delimiter': "OnWidget",
        'escapechar': "OnWidget",
        'quotechar': "OnWidget",
        'doublequote': "OnWidget",
        'self.has_header': "OnWidget",
        'skipinitialspace': "OnWidget",
    }

    def __init__(self, parent, csvfilepath):
        self.parent = parent
        self.csvfilepath = csvfilepath

        self.encoding = self.standard_encodings[0]

        if csvfilepath is None:
            dialect = csv.get_dialect(csv.list_dialects()[0])
            self.has_header = False
        else:
            dialect, self.has_header = sniff(self.csvfilepath)

        self.param_labels = []
        self.param_widgets = []

        self._setup_param_widgets()
        self._do_layout()
        self._update_settings(dialect)

        self.choice_dialects.SetSelection(0)

    def _setup_param_widgets(self):
        """Creates the parameter entry widgets and binds them to methods"""

        for parameter in self.csv_params:
            pname, ptype, plabel, phelp = parameter

            label = wx.StaticText(self.parent, -1, plabel)
            widget = self.type2widget[ptype](self.parent)

            # Append choicebox items and bind handler
            if pname in self.choices:
                widget.AppendItems(self.choices[pname])
                widget.SetValue = widget.Select
                widget.SetSelection(0)

            # Bind event handler to widget
            if ptype is bytes or ptype is str:
                event_type = wx.EVT_TEXT
            elif ptype is bool:
                event_type = wx.EVT_CHECKBOX
            else:
                event_type = wx.EVT_CHOICE

            handler = getattr(self, self.widget_handlers[pname])
            self.parent.Bind(event_type, handler, widget)

            # Tool tips
            label.SetToolTipString(phelp)
            widget.SetToolTipString(phelp)

            label.__name__ = wx.StaticText.__name__.lower()
            widget.__name__ = self.type2widget[ptype].__name__.lower()

            self.param_labels.append(label)
            self.param_widgets.append(widget)

            self.__setattr__("_".join([label.__name__, pname]), label)
            self.__setattr__("_".join([widget.__name__, pname]), widget)

    def _do_layout(self):
        """Sizer hell, returns a sizer that contains all widgets"""

        sizer_csvoptions = wx.FlexGridSizer(5, 4, 5, 5)

        # Adding parameter widgets to sizer_csvoptions
        leftpos = wx.LEFT | wx.ADJUST_MINSIZE
        rightpos = wx.RIGHT | wx.EXPAND

        current_label_margin = 0  # smaller for left column
        other_label_margin = 15

        for label, widget in zip(self.param_labels, self.param_widgets):
            sizer_csvoptions.Add(label, 0, leftpos, current_label_margin)
            sizer_csvoptions.Add(widget, 0, rightpos, current_label_margin)

            current_label_margin, other_label_margin = \
                other_label_margin, current_label_margin

        sizer_csvoptions.AddGrowableCol(1)
        sizer_csvoptions.AddGrowableCol(3)

        self.sizer_csvoptions = sizer_csvoptions

    def _update_settings(self, dialect):
        """Sets the widget settings to those of the chosen dialect"""

        # the first parameter is the dialect itself --> ignore
        for parameter in self.csv_params[2:]:
            pname, ptype, plabel, phelp = parameter

            widget = self._widget_from_p(pname, ptype)

            if ptype is tuple:
                ptype = object

            digest = Digest(acceptable_types=[ptype])

            if pname == 'self.has_header':
                if self.has_header is not None:
                    widget.SetValue(digest(self.has_header))
            else:
                value = getattr(dialect, pname)
                widget.SetValue(digest(value))

    def _widget_from_p(self, pname, ptype):
        """Returns a widget from its ptype and pname"""

        widget_name = self.type2widget[ptype].__name__.lower()
        widget_name = "_".join([widget_name, pname])
        return getattr(self, widget_name)

    def OnEncoding(self, event):
        """Stores encoding information"""

        self.encoding = event.GetString()
        event.Skip()

    def OnDialectChoice(self, event):
        """Updates all param widgets confirming to the selcted dialect"""

        dialect_name = event.GetString()
        value = list(self.choices['dialects']).index(dialect_name)

        if dialect_name == 'sniffer':
            if self.csvfilepath is None:
                event.Skip()
                return None
            dialect, self.has_header = sniff(self.csvfilepath)
        elif dialect_name == 'user':
            event.Skip()
            return None
        else:
            dialect = csv.get_dialect(dialect_name)

        self._update_settings(dialect)

        self.choice_dialects.SetValue(value)

    def OnWidget(self, event):
        """Update the dialect widget to 'user'"""

        self.choice_dialects.SetValue(len(self.choices['dialects']) - 1)
        event.Skip()

    def get_dialect(self):
        """Returns a new dialect that implements the current selection"""

        parameters = {}

        for parameter in self.csv_params[2:]:
            pname, ptype, plabel, phelp = parameter

            widget = self._widget_from_p(pname, ptype)

            if ptype is bytes or ptype is str:
                parameters[pname] = str(widget.GetValue())
            elif ptype is bool:
                parameters[pname] = widget.GetValue()
            elif pname == 'quoting':
                choice = self.choices['quoting'][widget.GetSelection()]
                parameters[pname] = getattr(csv, choice)
            else:
                raise TypeError(_("{type} unknown.").format(type=ptype))

        has_header = parameters.pop("self.has_header")

        try:
            csv.register_dialect('user', **parameters)

        except TypeError as err:
            msg = _("The dialect is invalid. \n "
                    "\nError message:\n{msg}").format(msg=err)
            dlg = wx.MessageDialog(self.parent, msg, style=wx.ID_CANCEL)
            dlg.ShowModal()
            dlg.Destroy()
            raise TypeError(err)

        return csv.get_dialect('user'), has_header


class CSVPreviewGrid(wx.grid.Grid):
    """The grid of the csv import parameter entry panel"""

    shape = [10, 10]

    digest_types = {
        'String': bytes,
        'Unicode': str,
        'Integer': int,
        'Float': float,
        'Boolean': bool,
        'Object': object,
    }

    # Only add date and time if dateutil is installed
    try:
        import datetime
        digest_types['Date'] = datetime.date
        digest_types['DateTime'] = datetime.datetime
        digest_types['Time'] = datetime.time
    except ImportError:
        pass

    def __init__(self, *args, **kwargs):
        self.has_header = kwargs.pop('has_header')
        self.csvfilepath = kwargs.pop('csvfilepath')

        super(CSVPreviewGrid, self).__init__(*args, **kwargs)

        self.parent = args[0]

        self.CreateGrid(*self.shape)

        self.dtypes = []

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnMouse)
        self.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnGridEditorCreated)

    def OnMouse(self, event):
        """Reduces clicks to enter an edit control"""

        self.SetGridCursor(event.Row, event.Col)
        self.EnableCellEditControl(True)
        event.Skip()

    def _set_properties(self):
        self.SetRowLabelSize(0)
        self.SetColLabelSize(0)
        self.EnableDragGridSize(0)

    def OnGridEditorCreated(self, event):
        """Used to capture Editor close events"""

        editor = event.GetControl()
        editor.Bind(wx.EVT_KILL_FOCUS, self.OnGridEditorClosed)

        event.Skip()

    def OnGridEditorClosed(self, event):
        """Event handler for end of output type choice"""

        try:
            dialect, self.has_header = \
                self.parent.csvwidgets.get_dialect()
        except TypeError:
            event.Skip()
            return 0

        self.fill_cells(dialect, self.has_header, choices=False)

    def fill_cells(self, dialect, has_header, choices=True):
        """Fills the grid for preview of csv data

        Parameters
        ----------
        dialect: csv,dialect
        \tDialect used for csv reader
        choices: Bool
        \tCreate and show choices

        """

        # Get columns from csv
        first_line = get_first_line(self.csvfilepath, dialect)
        self.shape[1] = no_cols = len(first_line)

        if no_cols > self.GetNumberCols():
            missing_cols = no_cols - self.GetNumberCols()
            self.AppendCols(missing_cols)

        elif no_cols < self.GetNumberCols():
            obsolete_cols = self.GetNumberCols() - no_cols
            self.DeleteCols(pos=no_cols - 1, numCols=obsolete_cols)

        # Retrieve type choices
        digest_keys = self.get_digest_keys()

        # Is a header present? --> Import as strings in first line
        if has_header:
            for i, header in enumerate(first_line):
                self.SetCellValue(0, i, header)

        if choices:
            # Add Choices
            for col in range(self.shape[1]):
                choice_renderer = ChoiceRenderer(self)
                choice_editor = wx.grid.GridCellChoiceEditor(
                    list(self.digest_types.keys()), False)
                self.SetCellRenderer(has_header, col, choice_renderer)
                self.SetCellEditor(has_header, col, choice_editor)
                self.SetCellValue(has_header, col, digest_keys[col])

        # Fill in the rest of the lines

        self.dtypes = []
        for key in self.get_digest_keys():
            try:
                self.dtypes.append(self.digest_types[key])
            except KeyError:
                self.dtypes.append(type(None))

        topleft = (has_header + 1, 0)

        digest_gen = csv_digest_gen(self.csvfilepath, dialect, has_header,
                                    self.dtypes)

        for row, col, val in cell_key_val_gen(digest_gen, self.shape, topleft):
            self.SetCellValue(row, col, val)

        self.Refresh()

    def get_digest_keys(self):
        """Returns a list of the type choices"""

        digest_keys = []
        for col in range(self.GetNumberCols()):
            digest_key = self.GetCellValue(self.has_header, col)
            if digest_key == "":
                digest_key = list(self.digest_types.keys())[0]
            digest_keys.append(digest_key)

        return digest_keys

    def get_digest_types(self):
        """Returns a list of the target types"""

        return [self.digest_types[digest_key]
                for digest_key in self.get_digest_keys()]


class CSVPreviewTextCtrl(wx.TextCtrl):
    """The grid of the csv export parameter entry panel"""

    preview_lines = 100  # Lines that are shown in preview

    def fill(self, data, dialect):
        """Fills the grid for preview of csv data

        Parameters
        ----------
        data: 2-dim array of strings
        \tData that is written to preview TextCtrl
        dialect: csv,dialect
        \tDialect used for csv reader

        """

        csvfile = io.StringIO()
        csvwriter = csv.writer(csvfile, dialect=dialect)

        for i, line in enumerate(data):
            csvwriter.writerow(list(encode_gen(line)))
            if i >= self.preview_lines:
                break

        preview = csvfile.getvalue()
        csvfile.close()
        preview = preview.decode("utf-8").replace("\r\n", "\n")
        self.SetValue(preview)


class CsvImportDialog(wx.Dialog):
    """Dialog for CSV import parameter choice with preview grid

    Parameters:
    -----------
    csvfilepath: string, defaults to '.'
    \tPath and Filename of CSV input file

    """

    def __init__(self, *args, **kwds):
        self.csvfilepath = kwds.pop("csvfilepath")
        self.csvfilename = os.path.split(self.csvfilepath)[1]

        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        wx.Dialog.__init__(self, *args, **kwds)

        self.csvwidgets = CsvParameterWidgets(self, self.csvfilepath)

        dialect, self.has_header = sniff(self.csvfilepath)

        self.grid = CSVPreviewGrid(self, -1,
                                   has_header=self.has_header,
                                   csvfilepath=self.csvfilepath)

        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "")

        self._set_properties()
        self._do_layout()

        self.grid.fill_cells(dialect, self.has_header)

    def _set_properties(self):
        """Sets dialog title and size limitations of the widgets"""

        title = _("CSV Import: {filepath}").format(filepath=self.csvfilename)
        self.SetTitle(title)
        self.SetSize((600, 600))

        for button in [self.button_cancel, self.button_ok]:
            button.SetMinSize((80, 28))

    def _do_layout(self):
        """Set sizers"""

        sizer_dialog = wx.FlexGridSizer(3, 1, 0, 0)

        # Sub sizers
        sizer_buttons = wx.FlexGridSizer(1, 3, 5, 5)

        # Adding buttons to sizer_buttons
        for button in [self.button_cancel, self.button_ok]:
            sizer_buttons.Add(button, 0, wx.ALL | wx.EXPAND, 5)

        sizer_buttons.AddGrowableRow(0)
        for col in range(3):
            sizer_buttons.AddGrowableCol(col)

        # Adding main components
        sizer_dialog.Add(self.csvwidgets.sizer_csvoptions,
                         0, wx.ALL | wx.EXPAND, 5)
        sizer_dialog.Add(self.grid,  1, wx.ALL | wx.EXPAND, 0)
        sizer_dialog.Add(sizer_buttons,  0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_dialog)

        sizer_dialog.AddGrowableRow(1)
        sizer_dialog.AddGrowableCol(0)

        self.Layout()
        self.Centre()


# end of class CsvImportDialog


class CsvExportDialog(wx.Dialog):
    """Dialog for CSV export parameter choice with preview text

    Parameters
    ----------
    data: 2-dim array of strings
    \tData that shall be written for preview

    """

    def __init__(self, *args, **kwds):

        self.data = kwds.pop('data')

        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        wx.Dialog.__init__(self, *args, **kwds)

        self.csvwidgets = CsvParameterWidgets(self, None)
        dialect = csv.get_dialect(csv.list_dialects()[0])
        self.has_header = False

        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        self.preview_textctrl = CSVPreviewTextCtrl(self, -1, style=style)

        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "")
        self.button_apply = wx.Button(self, wx.ID_APPLY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "")

        self._set_properties()
        self._do_layout()

        self.preview_textctrl.fill(data=self.data, dialect=dialect)

        self.Bind(wx.EVT_BUTTON, self.OnButtonApply, self.button_apply)

    def _set_properties(self):
        """Sets dialog title and size limitations of the widgets"""

        self.SetTitle("CSV Export")
        self.SetSize((600, 600))

        for button in [self.button_cancel, self.button_apply, self.button_ok]:
            button.SetMinSize((80, 28))

    def _do_layout(self):
        """Set sizers"""

        sizer_dialog = wx.FlexGridSizer(3, 1, 0, 0)

        # Sub sizers
        sizer_buttons = wx.FlexGridSizer(1, 3, 5, 5)

        # Adding buttons to sizer_buttons
        for button in [self.button_cancel, self.button_apply, self.button_ok]:
            sizer_buttons.Add(button, 0, wx.ALL | wx.EXPAND, 5)

        sizer_buttons.AddGrowableRow(0)
        for col in range(3):
            sizer_buttons.AddGrowableCol(col)

        # Adding main components
        sizer_dialog.Add(self.csvwidgets.sizer_csvoptions,
                         0, wx.ALL | wx.EXPAND, 5)
        sizer_dialog.Add(self.preview_textctrl,  1, wx.ALL | wx.EXPAND, 0)
        sizer_dialog.Add(sizer_buttons,  0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_dialog)

        sizer_dialog.AddGrowableRow(1)
        sizer_dialog.AddGrowableCol(0)

        self.Layout()
        self.Centre()

    def OnButtonApply(self, event):
        """Updates the preview_textctrl"""

        try:
            dialect, self.has_header = self.csvwidgets.get_dialect()
        except TypeError:
            event.Skip()
            return 0

        self.preview_textctrl.fill(data=self.data, dialect=dialect)

        event.Skip()

# end of class CsvImportDialog


class MacroDialog(wx.Frame, MainWindowEventMixin):
    """Macro management dialog"""

    def __init__(self, parent, macros, *args, **kwds):

        # begin wxGlade: MacroDialog.__init__
        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        self.parent = parent
        self.macros = macros

        wx.Frame.__init__(self, parent, *args, **kwds)

        self.splitter = wx.SplitterWindow(self, -1,
                                          style=wx.SP_3D | wx.SP_BORDER)

        self.upper_panel = wx.Panel(self.splitter, -1)
        self.lower_panel = wx.Panel(self.splitter, -1)

        style = wx.EXPAND | wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB | \
            wx.TE_MULTILINE
        self.codetext_ctrl = PythonSTC(self.upper_panel, -1, style=style)

        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH
        self.result_ctrl = wx.TextCtrl(self.lower_panel, -1, style=style)

        self.ok_button = wx.Button(self.lower_panel, wx.ID_OK)
        self.apply_button = wx.Button(self.lower_panel, wx.ID_APPLY)
        self.close_button = wx.Button(self.lower_panel, wx.ID_CLOSE)

        self._set_properties()
        self._do_layout()

        self.codetext_ctrl.SetText(self.macros)

        # Bindings
        self.Bind(stc.EVT_STC_MODIFIED, self.OnText, self.codetext_ctrl)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.ok_button)
        self.Bind(wx.EVT_BUTTON, self.OnApply, self.apply_button)
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.close_button)
        parent.Bind(self.EVT_CMD_MACROERR, self.update_result_ctrl)

        # States
        self._ok_pressed = False

    def _do_layout(self):
        """Layout sizers"""

        dialog_main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        upper_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lower_sizer = wx.FlexGridSizer(2, 1, 5, 0)
        lower_sizer.AddGrowableRow(0)
        lower_sizer.AddGrowableCol(0)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        upper_sizer.Add(self.codetext_ctrl, 1, wx.EXPAND, 0)
        lower_sizer.Add(self.result_ctrl, 1, wx.EXPAND, 0)
        lower_sizer.Add(button_sizer, 1, wx.EXPAND, 0)
        button_sizer.Add(self.ok_button, 1, wx.EXPAND, 0)
        button_sizer.Add(self.apply_button, 1, wx.EXPAND, 0)
        button_sizer.Add(self.close_button, 1, wx.EXPAND, 0)

        self.upper_panel.SetSizer(upper_sizer)
        self.lower_panel.SetSizer(lower_sizer)

        self.splitter.SplitHorizontally(self.upper_panel,
                                        self.lower_panel,
                                        400)
        dialog_main_sizer.Add(self.splitter, 1, wx.EXPAND, 0)
        self.SetSizer(dialog_main_sizer)
        self.Layout()

    def _set_properties(self):
        """Setup title, size and tooltips"""

        self.SetTitle(_("Macro list"))
        self.SetSize((800, 600))
        self.codetext_ctrl.SetToolTipString(_("Enter python code here."))
        self.ok_button.SetToolTipString(_("Accept all changes"))
        self.apply_button.SetToolTipString(_("Apply changes to current macro"))
        self.close_button.SetToolTipString(_("Remove current macro"))
        self.splitter.SetBackgroundStyle(wx.BG_STYLE_COLOUR)
        self.result_ctrl.SetMinSize((10, 10))

    def OnText(self, event):
        """Event handler for code control"""

        self.macros = self.codetext_ctrl.GetText()

    def OnOk(self, event):
        """Event handler for Ok button"""

        self._ok_pressed = True
        self.OnApply(event)

    def OnApply(self, event):
        """Event handler for Apply button"""

        # See if we have valid python
        try:
            ast.parse(self.macros)
        except:
            # Grab the traceback and print it for the user
            s = StringIO()
            e = exc_info()
            # usr_tb will more than likely be none because ast throws
            #   SytnaxErrorsas occurring outside of the current
            #   execution frame
            usr_tb = get_user_codeframe(e[2]) or None
            print_exception(e[0], e[1], usr_tb, None, s)
            post_command_event(self.parent, self.MacroErrorMsg,
                               err=s.getvalue())
            success = False
        else:
            self.result_ctrl.SetValue('')
            post_command_event(self.parent, self.MacroReplaceMsg,
                               macros=self.macros)
            post_command_event(self.parent, self.MacroExecuteMsg)
            success = True

        event.Skip()
        return success

    def OnClose(self, event):
        """Event handler for Cancel button"""

        # Warn if any unsaved changes
        if self.parent.grid.code_array.macros != self.macros:
            dlg = wx.MessageDialog(
                self, _("There are changes in the macro editor "
                        "which have not yet been applied.  Are you sure you "
                        "wish to close the editor?"), _("Close Editor"),
                wx.YES_NO | wx.ICON_WARNING)
            if dlg.ShowModal() == wx.ID_NO:
                return

        self.Destroy()

    def update_result_ctrl(self, event):
        """Update event result following execution by main window"""

        # Check to see if macro window still exists
        if not self:
            return

        printLen = 0
        self.result_ctrl.SetValue('')
        if hasattr(event, 'msg'):
            # Output of script (from print statements, for example)
            self.result_ctrl.AppendText(event.msg)
            printLen = len(event.msg)
        if hasattr(event, 'err'):
            # Error messages
            errLen = len(event.err)
            errStyle = wx.TextAttr(wx.RED)
            self.result_ctrl.AppendText(event.err)
            self.result_ctrl.SetStyle(printLen, printLen+errLen, errStyle)

        if not hasattr(event, 'err') or event.err == '':
            # No error passed.  Close dialog if user requested it.
            if self._ok_pressed:
                self.Destroy()
        self._ok_pressed = False


# end of class MacroDialog


class DimensionsEntryDialog(wx.Dialog):
    """Input dialog for the 3 dimensions of a grid"""

    def __init__(self, parent, *args, **kwds):
        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.MINIMIZE_BOX | wx.STAY_ON_TOP
        wx.Dialog.__init__(self, parent, *args, **kwds)

        self.Rows_Label = wx.StaticText(self, -1, _("Rows"),
                                        style=wx.ALIGN_CENTRE)
        self.X_DimensionsEntry = wx.TextCtrl(self, -1, "")
        self.Columns_Label = wx.StaticText(self, -1, _("Columns"),
                                           style=wx.ALIGN_CENTRE)
        self.Y_DimensionsEntry = wx.TextCtrl(self, -1, "")
        self.Tabs_Label = wx.StaticText(self, -1, _("Tables"),
                                        style=wx.ALIGN_CENTRE)
        self.Z_DimensionsEntry = wx.TextCtrl(self, -1, "")

        self.textctrls = [self.X_DimensionsEntry,
                          self.Y_DimensionsEntry,
                          self.Z_DimensionsEntry]

        self.ok_button = wx.Button(self, wx.ID_OK, "")
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, "")

        self._set_properties()
        self._do_layout()

        self.Bind(wx.EVT_TEXT, self.OnXDim, self.X_DimensionsEntry)
        self.Bind(wx.EVT_TEXT, self.OnYDim, self.Y_DimensionsEntry)
        self.Bind(wx.EVT_TEXT, self.OnZDim, self.Z_DimensionsEntry)

        self.dimensions = [1, 1, 1]

    def _set_properties(self):
        """Wx property setup"""

        self.SetTitle("New grid dimensions")
        self.cancel_button.SetDefault()

    def _do_layout(self):
        """Layout sizers"""

        label_style = wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        button_style = wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | \
            wx.ALIGN_CENTER_VERTICAL | wx.FIXED_MINSIZE

        grid_sizer_1 = wx.GridSizer(4, 2, 3, 3)

        grid_sizer_1.Add(self.Rows_Label, 0, label_style, 3)
        grid_sizer_1.Add(self.X_DimensionsEntry, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.Columns_Label, 0, label_style, 3)
        grid_sizer_1.Add(self.Y_DimensionsEntry, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.Tabs_Label, 0, label_style, 3)
        grid_sizer_1.Add(self.Z_DimensionsEntry, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.ok_button, 0, button_style, 3)
        grid_sizer_1.Add(self.cancel_button, 0, button_style, 3)
        self.SetSizer(grid_sizer_1)
        grid_sizer_1.Fit(self)
        self.Layout()
        self.X_DimensionsEntry.SetFocus()

    def _ondim(self, dimension, valuestring):
        """Converts valuestring to int and assigns result to self.dim

        If there is an error (such as an empty valuestring) or if
        the value is < 1, the value 1 is assigned to self.dim

        Parameters
        ----------

        dimension: int
        \tDimension that is to be updated. Must be in [1:4]
        valuestring: string
        \t A string that can be converted to an int

        """

        try:
            self.dimensions[dimension] = int(valuestring)
        except ValueError:
            self.dimensions[dimension] = 1
            self.textctrls[dimension].SetValue(str(1))

        if self.dimensions[dimension] < 1:
            self.dimensions[dimension] = 1
            self.textctrls[dimension].SetValue(str(1))

    def OnXDim(self, event):
        """Event handler for x dimension TextCtrl"""

        self._ondim(0, event.GetString())
        event.Skip()

    def OnYDim(self, event):
        """Event handler for y dimension TextCtrl"""

        self._ondim(1, event.GetString())
        event.Skip()

    def OnZDim(self, event):
        """Event handler for z dimension TextCtrl"""

        self._ondim(2, event.GetString())
        event.Skip()

# end of class DimensionsEntryDialog


class CellEntryDialog(wx.Dialog, GridEventMixin):
    """Allows entring three digits"""

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Cell Entry")

        self.parent = parent

        self.SetAutoLayout(True)
        VSPACE = 10

        fgs = wx.FlexGridSizer(0, 2)

        fgs.Add(wx.StaticText(self, -1, _("Goto cell:")))
        fgs.Add((1, 1))
        fgs.Add((1, VSPACE))
        fgs.Add((1, VSPACE))

        label = wx.StaticText(self, -1, _("Row: "))
        fgs.Add(label, 0, wx.ALIGN_RIGHT | wx.CENTER)
        self.row_textctrl = \
            wx.TextCtrl(self, -1, "", validator=IntValidator())
        fgs.Add(self.row_textctrl)

        fgs.Add((1, VSPACE))
        fgs.Add((1, VSPACE))

        label = wx.StaticText(self, -1, _("Column: "))
        fgs.Add(label, 0, wx.ALIGN_RIGHT | wx.CENTER)
        self.col_textctrl = \
            wx.TextCtrl(self, -1, "", validator=IntValidator())

        fgs.Add(self.col_textctrl)
        fgs.Add((1, VSPACE))
        fgs.Add((1, VSPACE))
        label = wx.StaticText(self, -1, _("Table: "))
        fgs.Add(label, 0, wx.ALIGN_RIGHT | wx.CENTER)
        self.tab_textctrl = \
            wx.TextCtrl(self, -1, "", validator=IntValidator())

        fgs.Add(self.tab_textctrl)

        buttons = wx.StdDialogButtonSizer()  # wx.BoxSizer(wx.HORIZONTAL)
        b = wx.Button(self, wx.ID_OK, _("OK"))
        b.SetDefault()
        buttons.AddButton(b)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL, _("Cancel")))
        buttons.Realize()

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(fgs, 1, wx.GROW | wx.ALL, 25)
        border.Add(buttons)
        self.SetSizer(border)
        border.Fit(self)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)

    def OnOk(self, event):
        """Posts a command event that makes the grid show the entered cell"""

        # Get key values from textctrls

        key_strings = [self.row_textctrl.GetValue(),
                       self.col_textctrl.GetValue(),
                       self.tab_textctrl.GetValue()]

        key = []

        for key_string in key_strings:
            try:
                key.append(int(key_string))
            except ValueError:
                key.append(0)

        # Post event

        post_command_event(self.parent, self.GotoCellMsg, key=tuple(key))


class AboutDialog(object):
    """Displays information about pyspread"""

    def __init__(self, *args, **kwds):
        # First we create and fill the info object
        parent = args[0]

        info = wx.AboutDialogInfo()
        info.Name = "pyspread"
        info.Version = config["version"]
        info.Copyright = "(C) Martin Manns"
        info.Description = wordwrap(
            _("A non-traditional Python spreadsheet application.\nPyspread is "
              "based on and written in the programming language Python."),
            350, wx.ClientDC(parent))
        info.WebSite = ("http://manns.github.io/pyspread/",
                        _("Pyspread Web site"))
        info.Developers = ["Martin Manns", "Jason Sexauer", "Vova Kolobok"]
        info.DocWriters = ["Martin Manns", "Bosko Markovic"]
        info.Translators = ["Joe Hansen", "Mark Haanen", "Yuri Chornoivan",
                            "Mario Blättermann", "Christian Kirbach",
                            "Martin Manns", "Andreas Noteng",
                            "Enrico Nicoletto", "Frédéric Marchal"]

        license_file = open(get_program_path() + "/COPYING", "r")
        license_text = license_file.read()
        license_file.close()

        info.License = wordwrap(license_text, 500, wx.ClientDC(parent))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)

    def _set_properties(self):
        """Setup title and label"""

        self.SetTitle(_("About pyspread"))

        label = _("pyspread {version}\nCopyright Martin Manns")
        label = label.format(version=VERSION)

        self.about_label.SetLabel(label)

    def _do_layout(self):
        """Layout sizers"""

        sizer_v = wx.BoxSizer(wx.VERTICAL)
        sizer_h = wx.BoxSizer(wx.HORIZONTAL)

        style = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL
        sizer_h.Add(self.logo_pyspread, 0, style, 10)
        sizer_h.Add(self.about_label, 0, style, 10)
        sizer_v.Add(sizer_h)
        self.SetSizer(sizer_v)
        sizer_v.Add(self.button_close, 0, style, 10)
        sizer_v.Fit(self)
        self.Layout()
        self.Centre()

    def OnClose(self, event):
        """Destroys dialog"""

        self.Destroy()

# end of class AboutDialog


class CheckBoxCtrl(wx.CheckBox):
    """CheckBox class that mimicks TextCtrl class"""

    def __init__(self, parent, uid, value, **kwargs):
        wx.CheckBox.__init__(self, parent, uid, **kwargs)
        self.SetValue(value)

    def get_value_str(self):
        """Returns string representation of CheckBox state"""

        return repr(self.GetValue())

    Value = property(get_value_str, wx.CheckBox.SetValue)

# end of class CheckBoxCtrl


class PreferencesDialog(wx.Dialog):
    """Dialog for changing pyspread's configuration preferences"""

    parameters = (
        ("max_unredo", {
            "label": _("Max. undo steps"),
            "tooltip": _("Maximum number of undo steps"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("grid_rows", {
            "label": _("Grid rows"),
            "tooltip": _("Number of grid rows when starting pyspread"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("grid_columns", {
            "label": _("Grid columns"),
            "tooltip": _("Number of grid columns when starting pyspread"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("grid_tables", {
            "label": _("Grid tables"),
            "tooltip": _("Number of grid tables when starting pyspread"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("max_result_length", {
            "label": _("Max. result length"),
            "tooltip": _("Maximum length of cell result string"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("timeout", {
            "label": _("Timeout"),
            "tooltip": _("Maximum time that an evaluation process may take."),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("timer_interval", {
            "label": _("Timer interval"),
            "tooltip": _("Interval for periodic updating of timed cells."),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 100, "allow_long": True},
            "prepocessor": int,
        }),
        ("gpg_key_fingerprint", {
            "label": _("GPG fingerprint"),
            "tooltip": _("Fingerprint of the GPG key for signing files"),
            "widget": wx.TextCtrl,
            "widget_params": {},
            "prepocessor": str,
        }),
    )

    def __init__(self, *args, **kwargs):
        kwargs["title"] = _("Preferences")
        kwargs["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME
        wx.Dialog.__init__(self, *args, **kwargs)

        self.labels = []

        # Controls for entering parameters, NOT only TextCtrls
        self.textctrls = []

        self.grid_sizer = wx.FlexGridSizer(0, 2, 2, 2)

        for parameter, info in self.parameters:
            label = info["label"]
            tooltip = info["tooltip"]
            value = config[parameter]

            self.labels.append(wx.StaticText(self, -1, label))
            self.labels[-1].SetToolTipString(tooltip)

            widget = info["widget"]
            preproc = info["prepocessor"]

            ctrl = widget(self, -1, preproc(value), **info["widget_params"])
            ctrl.SetToolTipString(tooltip)

            self.textctrls.append(ctrl)

            self.grid_sizer.Add(self.labels[-1], 0,
                                wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            self.grid_sizer.Add(self.textctrls[-1], 0,
                                wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                                2)

        self.ok_button = wx.Button(self, wx.ID_OK)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)
        self.grid_sizer.Add(self.ok_button, 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer.Add(self.cancel_button, 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        self.SetSizer(self.grid_sizer)

        self.grid_sizer.Fit(self)
        self.grid_sizer.AddGrowableCol(1)

        for row in range(len(self.parameters)):
            self.grid_sizer.AddGrowableRow(row)

        self.Layout()

        self.SetSize((300, -1))

# end of class PreferencesDialog


class GPGParamsDialog(wx.Dialog):
    """Gets GPG key parameters from user

    This dialog lets the user choose a new GPG key

    """

    def __init__(self, parent, ID, title, params):
        wx.Dialog.__init__(self, parent, ID, title)

        sizer = wx.FlexGridSizer(cols=2, vgap=5, hgap=5)

        label = wx.StaticText(self, -1, _("GPG key data"))
        sizer.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(wx.Panel(self, -1), 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.textctrls = []

        for labeltext, __ in params:
            label = wx.StaticText(self, -1, labeltext)
            sizer.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

            textctrl = wx.TextCtrl(self, -1, "", size=(80, -1))

            self.textctrls.append(textctrl)

            sizer.Add(textctrl, 1, wx.ALIGN_CENTRE | wx.ALL, 5)

        ok_button = wx.Button(self, wx.ID_OK)
        ok_button.SetToolTipString(_("Starts key generation."))
        ok_button.SetDefault()
        sizer.Add(ok_button)

        cancel_button = wx.Button(self, wx.ID_CANCEL)
        cancel_button.SetToolTipString(_("Exits pyspread."))
        sizer.Add(cancel_button)

        self.SetSizer(sizer)
        sizer.Fit(self)

# end of class GPGParamsDialog


class PasteAsDialog(wx.Dialog):
    """Gets paste as parameters from user

    Parameters
    ----------
    obj: Object
    \tObject that shall be pasted

    """

    def __init__(self, parent, id, obj, *args, **kwargs):
        title = _("Paste as")
        wx.Dialog.__init__(self, parent, id, title, *args, **kwargs)

        sizer = wx.FlexGridSizer(3, 2, 5, 5)

        self.dim_label = wx.StaticText(self, -1, _("Dimension of object"))
        self.dim_spinctrl = wx.SpinCtrl(self, -1, "Dim", (30, 50))
        self.dim_spinctrl.SetRange(0, self.get_max_dim(obj))

        self.transpose_label = wx.StaticText(self, -1, _("Transpose"))
        self.transpose_checkbox = wx.CheckBox(self, -1)

        ok_button = wx.Button(self, wx.ID_OK)
        cancel_button = wx.Button(self, wx.ID_CANCEL)

        sizer.Add(self.dim_label)
        sizer.Add(self.dim_spinctrl)

        sizer.Add(self.transpose_label)
        sizer.Add(self.transpose_checkbox)

        sizer.Add(ok_button)
        sizer.Add(cancel_button)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def get_max_dim(self, obj):
        """Returns maximum dimensionality over which obj is iterable <= 2"""

        try:
            iter(obj)

        except TypeError:
            return 0

        try:
            for o in obj:
                iter(o)
                break

        except TypeError:
            return 1

        return 2

    def get_parameters(self):
        """Returns dict of dialog content"""

        return {
            "dim": self.dim_spinctrl.GetValue(),
            "transpose": self.transpose_checkbox.GetValue()
        }

    parameters = property(get_parameters)

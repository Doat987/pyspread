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
_widgets
========

Provides:
---------
  1. PythonSTC: Syntax highlighting editor
  2. ImageComboBox: Base class for image combo boxes
  3. PenWidthComboBox: ComboBox for pen width selection
  4. MatplotlibStyleChoice: Base class for matplotlib chart style choices
  5. LineStyleComboBox: ChoiceBox for selection matplotlib line styles
  6. MarkerStyleComboBox: ChoiceBox for selection matplotlib marker styles
  7. FontChoiceCombobox: ComboBox for font selection
  8. BorderEditChoice: ComboBox for border selection
  9. BitmapToggleButton: Button that toggles through a list of bitmaps
 10. EntryLine: The line for entering cell code
 11. StatusBar: Main window statusbar
 12. TableChoiceIntCtrl: IntCtrl for choosing the current grid table

"""

import builtins
import keyword
from copy import copy
import time

try:
    import jedi
except ImportError:
    jedi = None

import wx
import wx.grid
import wx.adv
import wx.stc as stc
int
import src.lib.i18n as i18n
from src.lib.parsers import common_start
from src.lib._string_helpers import quote

from src.config import config
from src.sysvars import get_default_font, is_gtk, get_color

from ._events import post_command_event, EntryLineEventMixin
from ._events import StatusBarEventMixin, GridEventMixin, GridCellEventMixin
from ._events import MainWindowEventMixin, GridActionEventMixin

from .icons import icons

from gettext import gettext as _

# Maximum tooltip string length
MAX_TOOLTIP_LENGTH = 1000


class PythonSTC(stc.StyledTextCtrl):
    """Editor that highlights Python source code.

    Stolen from the wxPython demo.py

    """

    def __init__(self, *args, **kwargs):
        stc.StyledTextCtrl.__init__(self, *args, **kwargs)

        self._style()

        self.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(0, 0)

        self.SetViewWhiteSpace(False)

        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(78)

        # Setup a margin to hold fold markers
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)

        # Import symbol style from config file
        for marker in self.fold_symbol_style:
            self.MarkerDefine(*marker)

        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                          "face:%(helv)s,size:%(size)d" % self.faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Import text style specs from config file
        for spec in self.text_styles:
            self.StyleSetSpec(*spec)

        self.SetCaretForeground("BLUE")

        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 30)

    def _style(self):
        """Set editor style"""

        self.fold_symbols = 2

        """
        Fold symbols
        ------------

        The following styles are pre-defined:
          "arrows"      Arrow pointing right for contracted folders,
                        arrow pointing down for expanded
          "plusminus"   Plus for contracted folders, minus for expanded
          "circletree"  Like a flattened tree control using circular headers
                        and curved joins
          "squaretree"  Like a flattened tree control using square headers

        """

        self.faces = {
            'times': 'Times',
            'mono': 'Courier',
            'helv': wx.SystemSettings.GetFont(
                    wx.SYS_DEFAULT_GUI_FONT).GetFaceName(),
            'other': 'new century schoolbook',
            'size': 10,
            'size2': 8,
        }

        white = "white"
        gray = "#404040"

        # Fold circle tree symbol style from demo.py
        self.fold_symbol_style = [
            (stc.STC_MARKNUM_FOLDEROPEN,
             stc.STC_MARK_CIRCLEMINUS, white, gray),
            (stc.STC_MARKNUM_FOLDER,
             stc.STC_MARK_CIRCLEPLUS, white, gray),
            (stc.STC_MARKNUM_FOLDERSUB,
             stc.STC_MARK_VLINE, white, gray),
            (stc.STC_MARKNUM_FOLDERTAIL,
             stc.STC_MARK_LCORNERCURVE, white, gray),
            (stc.STC_MARKNUM_FOLDEREND,
             stc.STC_MARK_CIRCLEPLUSCONNECTED, white, gray),
            (stc.STC_MARKNUM_FOLDEROPENMID,
             stc.STC_MARK_CIRCLEMINUSCONNECTED, white, gray),
            (stc.STC_MARKNUM_FOLDERMIDTAIL,
             stc.STC_MARK_TCORNERCURVE, white, gray),
        ]

        """
        Text styles
        -----------

        The lexer defines what each style is used for, we just have to define
        what each style looks like.  The Python style set is adapted from
        Scintilla sample property files.

        """

        self.text_styles = [
            (stc.STC_STYLE_DEFAULT,
             "face:%(helv)s,size:%(size)d" % self.faces),
            (stc.STC_STYLE_LINENUMBER,
             "back:#C0C0C0,face:%(helv)s,size:%(size2)d" % self.faces),
            (stc.STC_STYLE_CONTROLCHAR,
             "face:%(other)s" % self.faces),
            (stc.STC_STYLE_BRACELIGHT,
             "fore:#FFFFFF,back:#0000FF,bold"),
            (stc.STC_STYLE_BRACEBAD,
             "fore:#000000,back:#FF0000,bold"),

            # Python styles
            # -------------

            # Default
            (stc.STC_P_DEFAULT,
             "fore:#000000,face:%(helv)s,size:%(size)d" % self.faces),

            # Comments
            (stc.STC_P_COMMENTLINE,
             "fore:#007F00,face:%(other)s,size:%(size)d" % self.faces),

            # Number
            (stc.STC_P_NUMBER,
             "fore:#007F7F,size:%(size)d" % self.faces),

            # String
            (stc.STC_P_STRING,
             "fore:#7F007F,face:%(helv)s,size:%(size)d" % self.faces),

            # Single quoted string
            (stc.STC_P_CHARACTER,
             "fore:#7F007F,face:%(helv)s,size:%(size)d" % self.faces),

            # Keyword
            (stc.STC_P_WORD,
             "fore:#00007F,bold,size:%(size)d" % self.faces),

            # Triple quotes
            (stc.STC_P_TRIPLE,
             "fore:#7F0000,size:%(size)d" % self.faces),

            # Triple double quotes
            (stc.STC_P_TRIPLEDOUBLE,
             "fore:#7F0000,size:%(size)d" % self.faces),

            # Class name definition
            (stc.STC_P_CLASSNAME,
             "fore:#0000FF,bold,underline,size:%(size)d" % self.faces),

            # Function or method name definition
            (stc.STC_P_DEFNAME,
             "fore:#007F7F,bold,size:%(size)d" % self.faces),

            # Operators
            (stc.STC_P_OPERATOR, "bold,size:%(size)d" % self.faces),

            # Identifiers
            (stc.STC_P_IDENTIFIER,
             "fore:#000000,face:%(helv)s,size:%(size)d" % self.faces),

            # Comment-blocks
            (stc.STC_P_COMMENTBLOCK,
             "fore:#7F7F7F,size:%(size)d" % self.faces),

            # End of line where string is not closed
            (stc.STC_P_STRINGEOL,
             "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d"
             % self.faces),
        ]

    def OnUpdateUI(self, evt):
        """Syntax highlighting while editing"""

        # check for matching braces
        brace_at_caret = -1
        brace_opposite = -1
        char_before = None
        caret_pos = self.GetCurrentPos()

        if caret_pos > 0:
            char_before = self.GetCharAt(caret_pos - 1)
            style_before = self.GetStyleAt(caret_pos - 1)

        # check before
        if char_before and chr(char_before) in "[]{}()" and \
           style_before == stc.STC_P_OPERATOR:
            brace_at_caret = caret_pos - 1

        # check after
        if brace_at_caret < 0:
            char_after = self.GetCharAt(caret_pos)
            style_after = self.GetStyleAt(caret_pos)

            if char_after and chr(char_after) in "[]{}()" and \
               style_after == stc.STC_P_OPERATOR:
                brace_at_caret = caret_pos

        if brace_at_caret >= 0:
            brace_opposite = self.BraceMatch(brace_at_caret)

        if brace_at_caret != -1 and brace_opposite == -1:
            self.BraceBadLight(brace_at_caret)
        else:
            self.BraceHighlight(brace_at_caret, brace_opposite)

    def OnMarginClick(self, evt):
        """When clicked, old and unfold as needed"""

        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.fold_all()
            else:
                line_clicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(line_clicked) & \
                   stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(line_clicked, True)
                        self.expand(line_clicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(line_clicked):
                            self.SetFoldExpanded(line_clicked, False)
                            self.expand(line_clicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(line_clicked, True)
                            self.expand(line_clicked, True, True, 100)
                    else:
                        self.ToggleFold(line_clicked)

    def fold_all(self):
        """Folds/unfolds all levels in the editor"""

        line_count = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for line_num in range(line_count):
            if self.GetFoldLevel(line_num) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(line_num)
                break

        line_num = 0

        while line_num < line_count:
            level = self.GetFoldLevel(line_num)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(line_num, True)
                    line_num = self.expand(line_num, True)
                    line_num = line_num - 1
                else:
                    last_child = self.GetLastChild(line_num, -1)
                    self.SetFoldExpanded(line_num, False)

                    if last_child > line_num:
                        self.HideLines(line_num + 1, last_child)

            line_num = line_num + 1

    def expand(self, line, do_expand, force=False, vislevels=0, level=-1):
        """Multi-purpose expand method from original STC class"""

        lastchild = self.GetLastChild(line, level)
        line += 1

        while line <= lastchild:
            if force:
                if vislevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            elif do_expand:
                self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    self.SetFoldExpanded(line, vislevels - 1)
                    line = self.expand(line, do_expand, force, vislevels - 1)

                else:
                    expandsub = do_expand and self.GetFoldExpanded(line)
                    line = self.expand(line, expandsub, force, vislevels - 1)
            else:
                line += 1

        return line

# end of class PythonSTC


class ImageComboBox(wx.adv.OwnerDrawnComboBox):
    """Base class for image combo boxes

    The class provides alternating backgrounds. Stolen from demo.py

    """

    def OnDrawBackground(self, dc, rect, item, flags):
        """Called for drawing the background area of each item

        Overridden from OwnerDrawnComboBox

        """

        # If the item is selected, or its item is even,
        # or if we are painting the combo control itself
        # then use the default rendering.

        if (item & 1 == 0 or flags & (wx.adv.ODCB_PAINTING_CONTROL |
                                      wx.adv.ODCB_PAINTING_SELECTED)):
            try:
                wx.adv.OwnerDrawnComboBox.OnDrawBackground(self, dc,
                                                           rect, item, flags)
            finally:
                return

        # Otherwise, draw every other background with
        # different color.

        bg_color = wx.Colour(240, 240, 250)
        dc.SetBrush(wx.Brush(bg_color))
        dc.SetPen(wx.Pen(bg_color))
        dc.DrawRectangleRect(rect)


class PenWidthComboBox(ImageComboBox):
    """Combo box for choosing line width for cell borders"""

    def OnDrawItem(self, dc, rect, item, flags):

        if item == wx.NOT_FOUND:
            return

        r = wx.Rect(*rect)  # make a copy
        r.Deflate(3, 5)

        pen_style = wx.SOLID
        if item == 0:
            pen_style = wx.TRANSPARENT
        pen = wx.Pen(dc.GetTextForeground(), item, pen_style)
        pen.SetCap(wx.CAP_BUTT)

        dc.SetPen(pen)

        # Draw the example line in the combobox
        dc.DrawLine(r.x + 5, r.y + r.height / 2,
                    r.x + r.width - 5, r.y + r.height / 2)

# end of class PenWidthComboBox

# Chart dialog widgets for matplotlib interaction
# -----------------------------------------------


class MatplotlibStyleChoice(wx.Choice):
    """Base class for line and marker choice for matplotlib charts"""

    # Style label and code are stored in styles as a list of tuples
    styles = []

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [style[0] for style in self.styles]
        wx.Choice.__init__(self, *args, **kwargs)

    def get_style_code(self, label):
        """Returns code for given label string

        Inverse of get_code

        Parameters
        ----------
        label: String
        \tLlabel string, field 0 of style tuple

        """

        for style in self.styles:
            if style[0] == label:
                return style[1]

        msg = _("Label {label} is invalid.").format(label=label)
        raise ValueError(msg)

    def get_label(self, code):
        """Returns string label for given code string

        Inverse of get_code

        Parameters
        ----------
        code: String
        \tCode string, field 1 of style tuple

        """

        for style in self.styles:
            if style[1] == code:
                return style[0]

        msg = _("Code {code} is invalid.").format(code=code)
        raise ValueError(msg)


class LineStyleComboBox(MatplotlibStyleChoice):
    """Combo box for choosing line style for matplotlib charts"""

    styles = [
        ("Solid line style", "-"),
        ("Dashed line style", "--"),
        ("Dash-dot line style", "-."),
        ("Dotted line style", ":"),
    ]


class MarkerStyleComboBox(MatplotlibStyleChoice):
    """Choice box for choosing matplotlib chart markers"""

    styles = [
        ("No marker", ""),
        ("Point marker", "."),
        ("Pixel marker", ","),
        ("Circle marker", "o"),
        ("Triangle_down marker", "v"),
        ("Triangle_up marker", "^"),
        ("Triangle_left marker", "<"),
        ("Triangle_right marker", ">"),
        ("Tri_down marker", "1"),
        ("Tri_up marker", "2"),
        ("Tri_left marker", "3"),
        ("Tri_right marker", "4"),
        ("Square marker", "s"),
        ("Pentagon marker", "p"),
        ("Star marker", "*"),
        ("Hexagon1 marker", "h"),
        ("hexagon2 marker", "H"),
        ("Plus marker", "+"),
        ("X marker", "x"),
        ("Diamond marker", "D"),
        ("Thin_diamond marker", "d"),
        ("Vline marker", "|"),
        ("Hline marker", "_"),
    ]


class CoordinatesComboBox(MatplotlibStyleChoice):
    """Combo box for choosing annotation coordinates for matplotlib charts"""

    styles = [
        ("Figure points", "figure points"),
        ("Figure pixels", "figure pixels"),
        ("Figure fraction", "figure fraction"),
        ("Axes points", "axes points"),
        ("Axes pixels", "axes pixels"),
        ("Axes fraction", "axes fraction"),
        ("Data", "data"),
        ("Offset points", "offset points"),
        ("Polar", "polar"),
    ]


# End of chart dialog widgets for matplotlib interaction
# ------------------------------------------------------


class FontChoiceCombobox(ImageComboBox):
    """Combo box for choosing fonts"""

    def OnDrawItem(self, dc, rect, item, flags):

        if item == wx.NOT_FOUND:
            return

        __rect = wx.Rect(*rect)  # make a copy
        __rect.Deflate(3, 5)

        font_string = self.GetString(item)

        font = get_default_font()
        font.SetFaceName(font_string)
        if not is_gtk():
            # Do not display fonts in font coice box for Windows
            font.SetFamily(wx.FONTFAMILY_SWISS)
        dc.SetFont(font)

        text_width, text_height = dc.GetTextExtent(font_string)
        text_x = __rect.x
        text_y = __rect.y + int((__rect.height - text_height) / 2.0)

        # Draw the example text in the combobox
        dc.DrawText(font_string, text_x, text_y)

# end of class FontChoiceCombobox


class BorderEditChoice(ImageComboBox):
    """Combo box for selecting the cell borders that shall be changed"""

    def __init__(self, *args, **kwargs):
        ImageComboBox.__init__(self, *args, **kwargs)
        self.SetSelection(0)

    def OnDrawItem(self, dc, rect, item, flags):

        if item == wx.NOT_FOUND:
            return

        r = wx.Rect(*rect)  # make a copy
        item_name = self.GetItems()[item]

        bmp = icons[item_name]

        icon = wx.Icon()
        icon.CopyFromBitmap(bmp)

        # Draw the border icon in the combobox
        dc.DrawIcon(icon, r.x, r.y)

    def OnMeasureItem(self, item):
        """Returns the height of the items in the popup"""

        item_name = self.GetItems()[item]
        return icons[item_name].GetHeight()

    def OnMeasureItemWidth(self, item):
        """Returns the height of the items in the popup"""

        item_name = self.GetItems()[item]
        return icons[item_name].GetWidth()

# end of class BorderEditChoice


class BitmapToggleButton(wx.BitmapButton):
    """Toggle button that goes through a list of bitmaps

    Parameters
    ----------
    bitmap_list: List of wx.Bitmap
    \tMust be non-empty

    """

    def __init__(self, parent, bitmap_list):

        assert len(bitmap_list) > 0

        self.bitmap_list = []
        for bmp in bitmap_list:
            if '__WXMSW__' not in wx.PlatformInfo:
                # Setting a mask fails on Windows.
                # Therefore transparency is set only for other platforms
                mask = wx.Mask(bmp, wx.BLUE)
                bmp.SetMask(mask)

            self.bitmap_list.append(bmp)

        self.state = 0

        super(BitmapToggleButton, self).__init__(
            parent, -1, self.bitmap_list[0], style=wx.BORDER_NONE)

        # For compatibility with toggle buttons
        setattr(self, "GetToolState", lambda x: self.state)

        self.Bind(wx.EVT_LEFT_UP, self.toggle, self)

    def toggle(self, event):
        """Toggles state to next bitmap"""

        if self.state < len(self.bitmap_list) - 1:
            self.state += 1
        else:
            self.state = 0

        self.SetBitmapLabel(self.bitmap_list[self.state])

        try:
            event.Skip()
        except AttributeError:
            pass

        """For compatibility with toggle buttons"""
        setattr(self, "GetToolState", lambda x: self.state)

# end of class BitmapToggleButton


class EntryLineToolbarPanel(wx.Panel):
    """Panel that contains an EntryLinePanel and a TableChoiceIntCtrl"""

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        try:
            self.SetBackgroundColour(get_color(wx.SYS_COLOUR_FRAMEBK))
        except AttributeError:
            # Does not work on wx 2.x
            pass

        self.parent = parent
        # Panel with EntryLine and button
        self.entry_line_panel = EntryLinePanel(self, parent,
                                               style=wx.NO_BORDER)

        # IntCtrl for table choice
        self.table_choice = TableChoiceIntCtrl(self, parent,
                                               config["grid_tables"])

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 2, 0, 0)

        main_sizer.Add(self.entry_line_panel, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(self.table_choice, 1, wx.ALL | wx.EXPAND, 1)

        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableCol(0)

        self.SetSizer(main_sizer)

        self.Layout()

# end of class EntryLineToolbarPanel


class EntryLinePanel(wx.Panel, GridEventMixin, GridActionEventMixin):
    """Panel that contains an EntryLine and a bitmap toggle button

    The button changes the state of the grid. If pressed, a grid selection
    is inserted into the EntryLine.

    """

    def __init__(self, parent, main_window, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        try:
            self.SetBackgroundColour(get_color(wx.SYS_COLOUR_FRAMEBK))
        except AttributeError:
            # Does not work on wx 2.x
            pass
        self.parent = parent
        self.main_window = main_window

        style = wx.TE_PROCESS_ENTER | wx.TE_MULTILINE
        self.entry_line = EntryLine(self, main_window, style=style)
        self.selection_toggle_button = \
            wx.ToggleButton(self, -1, size=(24, -1), label="\u25F0")

        tooltip = wx.ToolTip(_("Toggles link insertion mode."))
        self.selection_toggle_button.SetToolTip(tooltip)
        self.selection_toggle_button.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggle)

        if not is_gtk():
            # TODO: Selections still do not work right on Windows
            self.selection_toggle_button.Disable()

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 2, 0, 0)

        main_sizer.Add(self.entry_line, 0, wx.EXPAND, 0)
        main_sizer.Add(self.selection_toggle_button, 0, wx.EXPAND, 0)

        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableCol(0)

        self.SetSizer(main_sizer)

        self.Layout()

    def OnToggle(self, event):
        """Toggle button event handler"""

        if self.selection_toggle_button.GetValue():
            self.entry_line.last_selection = self.entry_line.GetSelection()
            self.entry_line.last_selection_string = \
                self.entry_line.GetStringSelection()
            self.entry_line.last_table = self.main_window.grid.current_table
            self.entry_line.Disable()
            post_command_event(self, self.EnterSelectionModeMsg)

        else:
            self.entry_line.Enable()
            post_command_event(self, self.GridActionTableSwitchMsg,
                               newtable=self.entry_line.last_table)
            post_command_event(self, self.ExitSelectionModeMsg)

# end of class EntryLinePanel


class EntryLine(wx.TextCtrl, EntryLineEventMixin, GridCellEventMixin,
                GridEventMixin, GridActionEventMixin):
    """"The line for entering cell code"""

    def __init__(self, parent, main_window, id=-1, *args, **kwargs):
        kwargs["style"] = wx.TE_PROCESS_ENTER | wx.TE_MULTILINE | \
            wx.TE_PROCESS_TAB | wx.NO_BORDER
        wx.TextCtrl.__init__(self, parent, id, *args, **kwargs)

        self.parent = parent
        self.main_window = main_window
        self.ignore_changes = False

        # Store last text selection of self before going into selection mode
        self.last_selection = None
        self.last_selection_string = None
        # The current table has to be stored on entering selection mode
        self.last_table = None

        main_window.Bind(self.EVT_ENTRYLINE_MSG, self.OnContentChange)
        main_window.Bind(self.EVT_CMD_SELECTION, self.OnGridSelection)
        main_window.Bind(self.EVT_ENTRYLINE_LOCK, self.OnLock)

        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

        self.SetToolTip(wx.ToolTip(_("Enter Python expression here.")))

        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.main_window.Bind(self.EVT_CMD_TABLE_CHANGED, self.OnTableChanged)

    def OnFocus(self, event):
        """SetFocus event handler"""

        event.Skip()

    def OnKillFocus(self, event):
        """KillFocus event handler"""

        event.Skip()

    def OnContentChange(self, event):
        """Event handler for updating the content"""

        if event.text is None:
            self.SetValue("")
        else:
            self.SetValue(event.text)

        event.Skip()

    def OnGridSelection(self, event):
        """Event handler for grid selection in selection mode adds text"""

        current_table = copy(self.main_window.grid.current_table)

        post_command_event(self, self.GridActionTableSwitchMsg,
                           newtable=self.last_table)
        if is_gtk():
            try:
                wx.Yield()
            except:
                pass

        sel_start, sel_stop = self.last_selection

        shape = self.main_window.grid.code_array.shape
        selection_string = event.selection.get_access_string(shape,
                                                             current_table)

        self.Replace(sel_start, sel_stop, selection_string)
        self.last_selection = sel_start, sel_start + len(selection_string)

        post_command_event(self, self.GridActionTableSwitchMsg,
                           newtable=current_table)

    def OnLock(self, event):
        """Event handler for locking the entry line"""

        self.Enable(not event.lock)

    def OnText(self, event):
        """Text event method evals the cell and updates the grid"""

        if not self.ignore_changes:
            post_command_event(self, self.CodeEntryMsg, code=event.GetString())

        self.main_window.grid.grid_renderer.cell_cache.clear()

        event.Skip()

    def OnChar(self, event):
        """Key event method

         * Forces grid update on <Enter> key
         * Handles insertion of cell access code

        """

        if not self.ignore_changes:

            # Handle special keys
            keycode = event.GetKeyCode()

            if keycode == 13 and not self.GetStringSelection():
                # <Enter> pressed and no selection --> Focus on grid
                self.main_window.grid.SetFocus()

                # Ignore <Ctrl> + <Enter> and Quote content
                if event.ControlDown():
                    self.SetValue(quote(self.GetValue()))

                # Do not process <Enter>
                return

            elif keycode == 13 and self.GetStringSelection():
                # <Enter> pressed and selection
                # --> Place cursor at end of selection and clear selection
                selection_start, selection_stop = self.Selection
                self.SetSelection(selection_stop, selection_stop)

                # Do not process <Enter>
                return

            elif keycode == 9 and jedi is None:
                # Ignore the <Tab>
                return

            elif keycode == 9 and jedi is not None:
                #  If auto completion library jedi is present
                # <Tab> pressed --> show docstring tooltip

                tiptext = ""

                code = "".join(self.GetValue().split("\n"))
                position = self.GetInsertionPoint()

                # Get the docstring
                code_array = self.parent.parent.parent.grid.code_array
                env = code_array.get_globals()
                try:
                    script = jedi.Interpreter(code, [env], line=1,
                                              column=position)
                except ValueError:
                    # Jedi has thrown an error
                    event.Skip()
                    return

                completions = script.completions()
                completes = [completion.complete for completion in completions]
                complete = common_start(completes)

                if complete and \
                   not self.GetSelection()[1] > self.GetSelection()[0]:
                    # There is a non-empty completion
                    insertion_point = self.GetInsertionPoint()
                    self.write(complete)
                    if len(completes) > 1:
                        self.SetSelection(insertion_point,
                                          insertion_point + len(complete))

                words = [completion.name for completion in completions]

                docs = []
                for completion in completions:
                    doc = completion.docstring(fast=False)
                    if not doc and code:
                        # Is the completion part of a module?
                        code_segment = \
                            code[:position+1].split()[-1]
                        module_name = code_segment.rsplit(".", 1)[0]
                        try:
                            module = env[module_name]
                            doc = getattr(module, completion.name).__doc__
                        except (KeyError, AttributeError):
                            pass

                    if not doc:
                        name = completion.name
                        try:
                            # Is the completion a builtin?
                            doc = getattr(__builtin__, name).__doc__
                        except AttributeError:
                            pass
                    docs.append(doc)

                try:
                    dws = [": ".join([w, d]) for w, d in zip(words, docs)]

                    tiptext = "\n \n".join(dws)
                except TypeError:
                    pass

                # Cut tiptext length because Tooltip fails for long strings

                self.SetToolTip(wx.ToolTip(tiptext[:MAX_TOOLTIP_LENGTH]))

                # Do not process <Tab>
                return

        event.Skip()

    def OnTableChanged(self, event):
        """Table changed event handler"""

        if hasattr(event, 'updated_cell'):
            # Event posted by cell edit widget.  Even more up to date
            #  than the current cell's contents
            try:
                self.SetValue(event.updated_cell)

            except TypeError:
                # None instead of string present
                pass

        else:
            current_cell = self.main_window.grid.actions.cursor
            current_cell_code = self.main_window.grid.code_array(current_cell)

            if current_cell_code is None:
                self.SetValue("")
            else:
                self.SetValue(current_cell_code)

        event.Skip()

# end of class EntryLine


class StatusBar(wx.StatusBar, StatusBarEventMixin, MainWindowEventMixin):
    """Main window statusbar"""

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)

        self.SetFieldsCount(2)

        self.size_changed = False

        safemode_bmp = icons["safe_mode"]

        self.safemode_staticbmp = wx.StaticBitmap(self, 1001, safemode_bmp)
        tooltip = wx.ToolTip(
            _("Pyspread is in safe mode.\nExpressions are not evaluated."))
        self.safemode_staticbmp.SetToolTip(tooltip)

        self.SetStatusWidths([-1, safemode_bmp.GetWidth() + 4])

        self.safemode_staticbmp.Hide()

        parent.Bind(self.EVT_STATUSBAR_MSG, self.OnMessage)
        parent.Bind(self.EVT_CMD_SAFE_MODE_ENTRY, self.OnSafeModeEntry)
        parent.Bind(self.EVT_CMD_SAFE_MODE_EXIT, self.OnSafeModeExit)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnMessage(self, event):
        """Statusbar message event handler"""

        self.SetStatusText(event.text)

    def OnSize(self, evt):
        self.Reposition()  # for normal size events

        # Set a flag so the idle time handler will also do the repositioning.
        # It is done this way to get around a buglet where GetFieldRect is not
        # accurate during the EVT_SIZE resulting from a frame maximize.
        self.size_changed = True

    def OnIdle(self, event):
        if self.size_changed:
            self.Reposition()

    def Reposition(self):
        """Reposition the checkbox"""

        rect = self.GetFieldRect(1)
        self.safemode_staticbmp.SetPosition((rect.x, rect.y))
        self.size_changed = False

    def OnSafeModeEntry(self, event):
        """Safe mode entry event handler"""

        self.safemode_staticbmp.Show(True)

        event.Skip()

    def OnSafeModeExit(self, event):
        """Safe mode exit event handler"""

        self.safemode_staticbmp.Hide()

        event.Skip()

# end of class StatusBar


class TableChoiceIntCtrl(wx.TextCtrl, GridEventMixin, GridActionEventMixin):
    """IntCtrl for choosing the current grid table"""

    def __init__(self, parent, main_window, no_tabs):
        self.parent = parent
        self.main_window = main_window
        self.no_tabs = no_tabs

        wx.TextCtrl.__init__(self, parent, style=wx.NO_BORDER)

        self.last_change_s = time.clock()

        tipmsg = _("For switching tables enter the table number or "
                   "use the mouse wheel.")
        self.SetToolTip(wx.ToolTip(tipmsg))

        # State for preventing to post GridActionTableSwitchMsg
        self.switching = False
        self.cursor_pos = 0

        self.Bind(wx.EVT_TEXT, self.OnInt)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.main_window.Bind(self.EVT_CMD_RESIZE_GRID, self.OnResizeGrid)
        self.main_window.Bind(self.EVT_CMD_TABLE_CHANGED, self.OnTableChanged)

    def change_max(self, no_tabs):
        """Updates to a new number of tables

        Fixes current table if out of bounds.

        Parameters
        ----------
        no_tabs: Integer
        \tNumber of tables for choice

        """

        self.no_tabs = no_tabs

        if self.GetValue() >= no_tabs:
            self.SetValue(no_tabs - 1)

    # Event handlers

    def OnResizeGrid(self, event):
        """Event handler for grid resizing"""

        self.change_max(event.shape[2])

    def _fromGUI(self, value):
        """
        Conversion function used in getting the value of the control.

        """

        # One or more of the underlying text control implementations
        # issue an intermediate EVT_TEXT when replacing the control's
        # value, where the intermediate value is an empty string.
        # So, to ensure consistency and to prevent spurious ValueErrors,
        # we make the following test, and react accordingly:
        #
        if value == '':
            if not self.IsNoneAllowed():
                return 0
            else:
                return
        else:
            try:
                return int(value)
            except ValueError:
                if self.IsLongAllowed():
                    try:
                        return int(value)
                    except ValueError:
                        wx.TextCtrl.SetValue(self, "0")
                        return 0
                else:
                    raise

    def OnInt(self, event):
        """IntCtrl event method that updates the current table"""

        value = event.GetValue()

        current_time = time.clock()
        if current_time < self.last_change_s + 0.01:
            return
        self.last_change_s = current_time

        self.cursor_pos = wx.TextCtrl.GetInsertionPoint(self) + 1

        if event.GetValue() > self.no_tabs - 1:
            value = self.no_tabs - 1

        self.switching = True
        post_command_event(self, self.GridActionTableSwitchMsg, newtable=value)
        self.switching = False

    def OnFocus(self, event):
        """Focus event handler"""

        wx.TextCtrl.SetInsertionPoint(self, self.cursor_pos)

    def OnMouseWheel(self, event):
        """Mouse wheel event handler"""

        # Prevent lost IntCtrl changes
        if self.switching:
            return

        value = self.GetValue()

        current_time = time.clock()
        if current_time < self.last_change_s + 0.01:
            return

        if event.GetWheelRotation() > 0:
            self.SetValue(min(value+1, self.no_tabs-1))
        else:
            self.SetValue(max(value-1, 0))

    def OnShapeChange(self, event):
        """Grid shape change event handler"""

        self.change_max(event.shape[2])

        event.Skip()

    def OnTableChanged(self, event):
        """Table changed event handler"""

        if hasattr(event, 'table'):
            self.SetValue(event.table)

        wx.TextCtrl.SetInsertionPoint(self, self.cursor_pos)

        event.Skip()

# end of class TableChoiceIntCtrl

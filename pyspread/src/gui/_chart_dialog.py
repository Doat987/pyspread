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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_chart_dialog
=============

Chart creation dialog with interactive matplotlib chart widget

Provides
--------

* ChartDialog: Chart dialog class

"""

# Architecture
# ------------
#
# Create widgets <Type>Editor for each type
# types are: bool, int, str, color, iterable, marker_style, line_style
# Each widget has a get_code method and a set_code method
#
# A SeriesBoxPanel is defined by:
# [panel_label, (matplotlib_key, widget, label, tooltip), ...]
#
# A <Seriestype>AttributesPanel(SeriesPanelBase) is defined by:
# [seriestype_key, SeriesBoxPanel, ...]
# It is derived from SeriesBasePanel and provides a widgets attribute
#
# SeriesPanelBase provides a method
# __iter__ that yields (key, code) for each widget
#
# SeriesPanel provides a TreeBook of series types
# It is defined by:
# [(seriestype_key, seriestype_label, seriestype_image,
#                                     <Seriestype>AttributesPanel), ...]
#
# AllSeriesPanel provides a flatnotebook with one tab per series
#
# FigureAttributesPanel is equivalent to a <Seriestype>AttributesPanel
#
# FigurePanel provides a matplotlib chart drawing
#
# ChartDialog provides FigureAttributesPanel, Flatnotebook of SeriesPanels,
#                      FigurePanel


import wx
import matplotlib
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import wx.lib.colourselect as csel
from wx.lib.intctrl import IntCtrl, EVT_INT
import wx.lib.agw.flatnotebook as fnb

from ._widgets import LineStyleComboBox, MarkerStyleComboBox
from ._widgets import CoordinatesComboBox
from ._events import post_command_event, ChartDialogEventMixin
import src.lib.i18n as i18n
import src.lib.charts as charts
from src.lib.parsers import color2code, code2color, parse_dict_strings
from src.lib.parsers import unquote_string
from .icons import icons
from sysvars import get_default_font, get_color

# Use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


# --------------
# Editor widgets
# --------------


class BoolEditor(wx.CheckBox, ChartDialogEventMixin):
    """Editor widget for bool values"""

    def __init__(self, *args, **kwargs):
        wx.CheckBox.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(wx.EVT_CHECKBOX, self.OnChecked)

    def get_code(self):
        """Returns '0' or '1'"""

        return self.GetValue()

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of bool value

        """

        # If string representations of False are in the code
        # then it has to be converted explicitly

        if code == "False" or code == "0":
            code = False

        self.SetValue(bool(code))

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnChecked(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class IntegerEditor(IntCtrl, ChartDialogEventMixin):
    """Editor widget for integer values"""

    def __init__(self, *args, **kwargs):
        IntCtrl.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(EVT_INT, self.OnInt)

    def get_code(self):
        """Returns string representation of Integer"""

        return str(self.GetValue())

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of integer value

        """

        self.SetValue(int(code))

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnInt(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class StringEditor(wx.TextCtrl, ChartDialogEventMixin):
    """Editor widget for string values"""

    def __init__(self, *args, **kwargs):
        wx.TextCtrl.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(wx.EVT_TEXT, self.OnText)

    def get_code(self):
        """Returns code representation of value of widget"""

        return self.GetValue()

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        self.SetValue(code)

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnText(self, event):
        """Text entry event handler"""

        post_command_event(self, self.DrawChartMsg)


class TextEditor(wx.Panel, ChartDialogEventMixin):
    """Editor widget for text objects

    The editor provides a taxt ctrl, a font button and a color chooser

    """

    style_wx2mpl = {
        wx.FONTSTYLE_ITALIC: "italic",
        wx.FONTSTYLE_NORMAL: "normal",
        wx.FONTSTYLE_SLANT: "oblique",
    }

    style_mpl2wx = dict((v, k) for k, v in style_wx2mpl.items())

    weight_wx2mpl = {
        wx.FONTWEIGHT_BOLD: "bold",
        wx.FONTWEIGHT_NORMAL: "normal",
        wx.FONTWEIGHT_LIGHT: "light",
    }

    weight_mpl2wx = dict((v, k) for k, v in weight_wx2mpl.items())

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self.textctrl = wx.TextCtrl(self, -1)
        self.fontbutton = wx.Button(self, -1, label="\u2131", size=(24, 24))
        self.colorselect = csel.ColourSelect(self, -1, size=(24, 24))

        self.value = ""

        self.chosen_font = None

        self.font_face = None
        self.font_size = None
        self.font_style = None
        self.font_weight = None
        self.color = get_color

        self.__bindings()
        self.__do_layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.textctrl.Bind(wx.EVT_TEXT, self.OnText)
        self.fontbutton.Bind(wx.EVT_BUTTON, self.OnFont)
        self.Bind(csel.EVT_COLOURSELECT, self.OnColor)

    def __do_layout(self):
        grid_sizer = wx.FlexGridSizer(1, 3, 0, 0)

        grid_sizer.Add(self.textctrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.fontbutton, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.colorselect, 1, wx.ALL | wx.EXPAND, 2)

        grid_sizer.AddGrowableCol(0)

        self.SetSizer(grid_sizer)

        self.fontbutton.SetToolTip(wx.ToolTip(_("Text font")))
        self.colorselect.SetToolTip(wx.ToolTip(_("Text color")))

        self.Layout()

    def get_code(self):
        """Returns code representation of value of widget"""

        return self.textctrl.GetValue()

    def get_kwargs(self):
        """Return kwargs dict for text"""

        kwargs = {}

        if self.font_face:
            kwargs["fontname"] = repr(self.font_face)
        if self.font_size:
            kwargs["fontsize"] = repr(self.font_size)
        if self.font_style in self.style_wx2mpl:
            kwargs["fontstyle"] = repr(self.style_wx2mpl[self.font_style])
        if self.font_weight in self.weight_wx2mpl:
            kwargs["fontweight"] = repr(self.weight_wx2mpl[self.font_weight])

        kwargs["color"] = color2code(self.colorselect.GetValue())

        code = ", ".join(repr(key) + ": " + kwargs[key] for key in kwargs)

        code = "{" + code + "}"

        return code

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        self.textctrl.SetValue(code)

    def set_kwargs(self, code):
        """Sets widget from kwargs string

        Parameters
        ----------
        code: String
        \tCode representation of kwargs value

        """

        kwargs = {}

        kwarglist = list(parse_dict_strings(code[1:-1]))

        for kwarg, val in zip(kwarglist[::2], kwarglist[1::2]):
            kwargs[unquote_string(kwarg)] = val

        for key in kwargs:
            if key == "color":
                color = code2color(kwargs[key])
                self.colorselect.SetOwnForegroundColour(color)

            elif key == "fontname":
                self.font_face = unquote_string(kwargs[key])

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()
                self.chosen_font.SetFaceName(self.font_face)

            elif key == "fontsize":
                if kwargs[key]:
                    self.font_size = int(kwargs[key])
                else:
                    self.font_size = get_default_font().GetPointSize()

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()

                self.chosen_font.SetPointSize(self.font_size)

            elif key == "fontstyle":
                self.font_style = \
                    self.style_mpl2wx[unquote_string(kwargs[key])]

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()

                self.chosen_font.SetStyle(self.font_style)

            elif key == "fontweight":
                self.font_weight = \
                    self.weight_mpl2wx[unquote_string(kwargs[key])]

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()

                self.chosen_font.SetWeight(self.font_weight)

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnText(self, event):
        """Text entry event handler"""

        post_command_event(self, self.DrawChartMsg)

    def OnFont(self, event):
        """Check event handler"""

        font_data = wx.FontData()

        # Disable color chooser on Windows
        font_data.EnableEffects(False)

        if self.chosen_font:
            font_data.SetInitialFont(self.chosen_font)

        dlg = wx.FontDialog(self, font_data)

        if dlg.ShowModal() == wx.ID_OK:
            font_data = dlg.GetFontData()

            font = self.chosen_font = font_data.GetChosenFont()

            self.font_face = font.GetFaceName()
            self.font_size = font.GetPointSize()
            self.font_style = font.GetStyle()
            self.font_weight = font.GetWeight()

        dlg.Destroy()

        post_command_event(self, self.DrawChartMsg)

    def OnColor(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class TickParamsEditor(wx.Panel, ChartDialogEventMixin):
    """Editor widget for axis ticks

    The widget contains: direction, pad, labelsize, bottom, top, left, right

    """

    choice_labels = [_("Inside"), _("Outside"), _("Both")]
    choice_params = ["in", "out", "inout"]

    choice_label2param = dict(list(zip(choice_labels, choice_params)))
    choice_param2label = dict(list(zip(choice_params, choice_labels)))

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self.attrs = {
            "direction": None,
            "pad": None,
            "top": None,
            "right": None,
            "labelsize": None,
        }

        self.direction_choicectrl = wx.Choice(self, -1,
                                              choices=self.choice_labels)
        self.pad_label = wx.StaticText(self, -1, _("Padding"), size=(-1, 15))
        self.pad_intctrl = IntCtrl(self, -1, allow_none=True, value=None,
                                   limited=True)
        self.size_label = wx.StaticText(self, -1, _("Size"), size=(-1, 15))
        self.labelsize_intctrl = IntCtrl(self, -1, allow_none=True, value=None,
                                         min=1, max=99, limited=True)

        style = wx.ALIGN_RIGHT | wx.CHK_3STATE
        self.sec_checkboxctrl = wx.CheckBox(self, -1, label=_("Secondary"),
                                            style=style)

        self.sec_checkboxctrl.Set3StateValue(wx.CHK_UNDETERMINED)
        self.__bindings()
        self.__do_layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.direction_choicectrl.Bind(wx.EVT_CHOICE, self.OnDirectionChoice)
        self.sec_checkboxctrl.Bind(wx.EVT_CHECKBOX, self.OnSecondaryCheckbox)
        self.pad_intctrl.Bind(EVT_INT, self.OnPadIntCtrl)
        self.labelsize_intctrl.Bind(EVT_INT, self.OnLabelSizeIntCtrl)

    def __do_layout(self):
        grid_sizer = wx.FlexGridSizer(2, 3, 0, 0)
        grid_sizer.Add(self.sec_checkboxctrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.pad_label, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.pad_intctrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.direction_choicectrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.size_label, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.labelsize_intctrl, 1, wx.ALL | wx.EXPAND, 2)

        grid_sizer.AddGrowableCol(0)
        grid_sizer.AddGrowableCol(1)
        grid_sizer.AddGrowableCol(2)

        self.SetSizer(grid_sizer)

        # Tooltips
        dir_tip = _("Puts ticks inside the axes, outside the axes, or both.")
        self.direction_choicectrl.SetToolTip(wx.ToolTip(dir_tip))
        pad_tip = _("Distance in points between tick and label.")
        self.pad_intctrl.SetToolTip(wx.ToolTip(pad_tip))
        label_tip = _("Tick label font size in points.")
        self.labelsize_intctrl.SetToolTip(wx.ToolTip(label_tip))

        self.Layout()

    def get_code(self):
        """Returns code representation of value of widget"""

        return ""

    def get_kwargs(self):
        """Return kwargs dict for text"""

        kwargs = {}

        for attr in self.attrs:
            val = self.attrs[attr]
            if val is not None:
                kwargs[attr] = repr(val)

        code = ", ".join(repr(key) + ": " + kwargs[key] for key in kwargs)

        code = "{" + code + "}"

        return code

    def set_code(self, code):
        """Sets widget from code string, does nothing here

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        pass

    def set_kwargs(self, code):
        """Sets widget from kwargs string

        Parameters
        ----------
        code: String
        \tCode representation of kwargs value

        """

        kwargs = {}

        kwarglist = list(parse_dict_strings(code[1:-1]))

        for kwarg, val in zip(kwarglist[::2], kwarglist[1::2]):
            kwargs[unquote_string(kwarg)] = val

        for key in kwargs:
            if key == "direction":
                self.attrs[key] = unquote_string(kwargs[key])
                label = self.choice_param2label[self.attrs[key]]
                label_list = self.direction_choicectrl.Items
                self.direction_choicectrl.SetSelection(label_list.index(label))

            elif key == "pad":
                self.attrs[key] = int(kwargs[key])
                self.pad_intctrl.SetValue(self.attrs[key])

            elif key in ["top", "right"]:
                self.attrs[key] = (not kwargs[key] == "False")
                if self.attrs[key]:
                    self.sec_checkboxctrl.Set3StateValue(wx.CHK_CHECKED)
                else:
                    self.sec_checkboxctrl.Set3StateValue(wx.CHK_UNCHECKED)

            elif key == "labelsize":
                self.attrs[key] = int(kwargs[key])
                self.labelsize_intctrl.SetValue(self.attrs[key])

    # Properties

    code = property(get_code, set_code)

    # Event handlers

    def OnDirectionChoice(self, event):
        """Direction choice event handler"""

        label = self.direction_choicectrl.GetItems()[event.GetSelection()]
        param = self.choice_label2param[label]
        self.attrs["direction"] = param

        post_command_event(self, self.DrawChartMsg)

    def OnSecondaryCheckbox(self, event):
        """Top Checkbox event handler"""

        self.attrs["top"] = event.IsChecked()
        self.attrs["right"] = event.IsChecked()

        post_command_event(self, self.DrawChartMsg)

    def OnPadIntCtrl(self, event):
        """Pad IntCtrl event handler"""

        self.attrs["pad"] = event.GetValue()

        post_command_event(self, self.DrawChartMsg)

    def OnLabelSizeIntCtrl(self, event):
        """Label size IntCtrl event handler"""

        self.attrs["labelsize"] = event.GetValue()

        post_command_event(self, self.DrawChartMsg)


class ColorEditor(csel.ColourSelect, ChartDialogEventMixin):
    """Editor widget for 3-tuples of floats that represent color"""

    def __init__(self, *args, **kwargs):
        csel.ColourSelect.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(csel.EVT_COLOURSELECT, self.OnColor)

    def get_code(self):
        """Returns string representation of Integer"""

        return color2code(self.GetValue())

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tString representation of 3 tuple of float

        """

        self.SetColour(code2color(code))

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnColor(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class StyleEditorMixin(object):
    """Mixin class for stzle editors that are based on MatplotlibStyleChoice"""

    def bindings(self):
        """Binds events to handlers"""

        self.Bind(wx.EVT_CHOICE, self.OnStyle)

    def get_code(self):
        """Returns code representation of value of widget"""

        selection = self.GetSelection()

        if selection == wx.NOT_FOUND:
            selection = 0

        # Return code string
        return self.styles[selection][1]

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        for i, (_, style_code) in enumerate(self.styles):
            if code == style_code:
                self.SetSelection(i)

    # Properties

    code = property(get_code, set_code)

    # Handlers
    # --------

    def OnStyle(self, event):
        """Marker style event handler"""

        post_command_event(self, self.DrawChartMsg)


class MarkerStyleEditor(MarkerStyleComboBox, ChartDialogEventMixin,
                        StyleEditorMixin):
    """Editor widget for marker style string values"""

    def __init__(self, *args, **kwargs):
        MarkerStyleComboBox.__init__(self, *args, **kwargs)

        self.bindings()


class LineStyleEditor(LineStyleComboBox, ChartDialogEventMixin,
                      StyleEditorMixin):
    """Editor widget for line style string values"""

    def __init__(self, *args, **kwargs):
        LineStyleComboBox.__init__(self, *args, **kwargs)

        self.bindings()


class CoordinatesEditor(CoordinatesComboBox, ChartDialogEventMixin,
                        StyleEditorMixin):
    """Editor widget for line style string values"""

    def __init__(self, *args, **kwargs):
        CoordinatesComboBox.__init__(self, *args, **kwargs)

        self.bindings()

# -------------
# Panel widgets
# -------------


class SeriesBoxPanel(wx.Panel):
    """Box panel that contains labels and widgets

    Parameters
    ----------

    * panel_label: String
    \tLabel that is displayed left of the widget
    * labels: List of strings
    \tWidget labels
    * widgets: List of class instances
    \tWidget instance list must be as long as labels

    """

    def __init__(self, parent, box_label, labels, widget_clss, widget_codes,
                 tooltips):

        wx.Panel.__init__(self, parent, -1)

        self.staticbox = wx.StaticBox(self, -1, box_label)

        self.labels = [wx.StaticText(self, -1, label) for label in labels]

        self.widgets = []

        for widget_cls, widget_code, label, tooltip in \
                zip(widget_clss, widget_codes, self.labels, tooltips):
            widget = widget_cls(self, -1)
            widget.code = widget_code
            self.widgets.append(widget)
            if tooltip:
                widget.SetToolTipString(tooltip)

        self.__do_layout()

    def __do_layout(self):
        box_sizer = wx.StaticBoxSizer(self.staticbox, wx.HORIZONTAL)
        grid_sizer = wx.FlexGridSizer(len(self.labels), 2, 0, 0)

        for label, widget in zip(self.labels, self.widgets):
            grid_sizer.Add(label, 1, wx.ALL | wx.EXPAND, 2)
            grid_sizer.Add(widget, 1, wx.ALL | wx.EXPAND, 2)

        grid_sizer.AddGrowableCol(1)
        box_sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(box_sizer)

        self.Layout()


class SeriesAttributesPanelBase(wx.Panel):
    """Base class for <Seriestype>AttributesPanel and FigureAttributesPanel"""

    def __init__(self, parent, series_data, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.data = {}
        self.data.update(self.default_data)

        self.update(series_data)

        self.box_panels = []

        for box_label, keys in self.boxes:
            labels = []
            widget_clss = []
            widget_codes = []
            tooltips = []

            for key in keys:
                widget_label, widget_cls, widget_default = self.data[key]

                widget_clss.append(widget_cls)
                widget_codes.append(widget_default)
                labels.append(widget_label)
                try:
                    tooltips.append(self.tooltips[key])
                except KeyError:
                    tooltips.append("")

            self.box_panels.append(SeriesBoxPanel(self, box_label, labels,
                                                  widget_clss, widget_codes,
                                                  tooltips))

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(max(3, len(self.box_panels)), 1, 0, 0)

        for box_panel in self.box_panels:
            main_sizer.Add(box_panel, 1, wx.ALL | wx.EXPAND, 2)

        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableRow(1)
        main_sizer.AddGrowableRow(2)

        self.SetSizer(main_sizer)

        self.Layout()

    def __iter__(self):
        """Yields (key, code) for each widget"""

        for box_panel, (_, keys) in zip(self.box_panels, self.boxes):
            for widget, key in zip(box_panel.widgets, keys):
                yield key, widget

    def update(self, series_data):
        """Updates self.data from series data

        Parameters
        ----------
         * series_data: dict
        \tKey value pairs for self.data, which correspond to chart attributes

        """

        for key in series_data:
            try:
                data_list = list(self.data[key])
                data_list[2] = str(series_data[key])
                self.data[key] = tuple(data_list)
            except KeyError:
                pass


class PlotAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides plot series attributes in multiple boxed panels"""

    # Data for series plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "label": (_("Label"), StringEditor, ""),
        "xdata": (_("X"), StringEditor, ""),
        "ydata": (_("Y"), StringEditor, ""),
        "linestyle": (_("Style"), LineStyleEditor, '-'),
        "linewidth": (_("Width"), IntegerEditor, "1"),
        "color": (_("Color"), ColorEditor, "(0, 0, 0)"),
        "marker": (_("Style"), MarkerStyleEditor, ""),
        "markersize": (_("Size"), IntegerEditor, "5"),
        "markerfacecolor": (_("Face color"), ColorEditor, "(0, 0, 0)"),
        "markeredgecolor": (_("Edge color"), ColorEditor, "(0, 0, 0)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["label", "xdata", "ydata"]),
        (_("Line"), ["linestyle", "linewidth", "color"]),
        (_("Marker"), ["marker", "markersize", "markerfacecolor",
                       "markeredgecolor"]),
    ]

    tooltips = {
        "label": _("String or anything printable with ‘%s’ conversion"),
        "xdata": _("The data np.array for x\n"
                   "Code must eval to 1D array."),
        "ydata": _("The data np.array for y\n"
                   "Code must eval to 1D array."),
        "linewidth": _("The line width in points"),
        "marker": _("The line marker"),
        "markersize": _("The marker size in points"),
    }


class BarAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides bar series attributes in multiple boxed panels"""

    # Data for bar plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "label": (_("Label"), StringEditor, ""),
        "left": (_("Left positions"), StringEditor, ""),
        "height": (_("Bar heights"), StringEditor, ""),
        "width": (_("Bar widths"), StringEditor, ""),
        "bottom": (_("Bar bottoms"), StringEditor, ""),
        "color": (_("Bar color"), ColorEditor, "(0, 0, 0)"),
        "edgecolor": (_("Edge color"), ColorEditor, "(0, 0, 0)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["label", "left", "height", "width", "bottom"]),
        (_("Bar"), ["color", "edgecolor"]),
    ]

    tooltips = {
        "label": _("String or anything printable with ‘%s’ conversion"),
        "left": _("The x coordinates of the left sides of the bars"),
        "height": _("The heights of the bars"),
        "width": _("The widths of the bars"),
        "bottom": _("The y coordinates of the bottom edges of the bars"),
    }


class BoxplotAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides bar series attributes in multiple boxplot panels"""

    # Data for boxplot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "x": (_("Series"), StringEditor, ""),
        "widths": (_("Box widths"), StringEditor, "0.5"),
        "vert": (_("Vertical"), BoolEditor, True),
        "sym":  (_("Flier"), MarkerStyleEditor, "+"),
        "notch": (_("Notch"), BoolEditor, False),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["x"]),
        (_("Box plot"), ["widths", "vert", "sym", "notch"]),
    ]

    tooltips = {
        "x": _("An array or a sequence of vectors"),
        "widths": _("Either a scalar or a vector and sets the width of each "
                    "box\nThe default is 0.5, or\n0.15*(distance between "
                    "extreme positions)\nif that is smaller"),
        "vert": _("If True then boxes are drawn vertical\n"
                  "If False then boxes are drawn horizontal"),
        "sym": _("The symbol for flier points\nEnter an empty string (‘’)\n"
                 "if you don’t want to show fliers"),
        "notch": _("False produces a rectangular box plot\n"
                   "True produces a notched box plot"),
    }


class HistogramAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides bar series attributes in histogram panels"""

    # Data for histogram
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "label": (_("Label"), StringEditor, ""),
        "x": (_("Series"), StringEditor, ""),
        "bins": (_("Bins"), IntegerEditor, "10"),
        "normed": (_("Normed"), BoolEditor, False),
        "cumulative": (_("Cumulative"), BoolEditor, False),
        "color": (_("Color"), ColorEditor, "(0, 0, 1)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["label", "x"]),
        (_("Histogram"), ["bins", "normed", "cumulative", "color"]),
    ]

    tooltips = {
        "label": _("String or anything printable with ‘%s’ conversion"),
        "x": _("Histogram data series\nMultiple data sets can be provided "
               "as a list or as a 2-D ndarray in which each column"
               "is a dataset. Note that the ndarray form is transposed "
               "relative to the list form."),
        "bins": _("Either an integer number of bins or a bin sequence"),
        "normed": _("If True then the first element is the counts normalized"
                    "to form a probability density, i.e., n/(len(x)*dbin)."),
        "cumulative": _("If True then each bin gives the counts in that bin"
                        "\nplus all bins for smaller values."),
    }


class PieAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides pie series attributes in multiple boxed panels"""

    # Data for pie plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "x": (_("Series"), StringEditor, ""),
        "labels": (_("Labels"), StringEditor, ""),
        "colors": (_("Colors"), StringEditor, ""),
        "startangle": (_("Start angle"), IntegerEditor, "0"),
        "shadow": (_("Shadow"), BoolEditor, False),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["x"]),
        (_("Pie"), ["labels", "colors", "startangle", "shadow"]),
    ]

    tooltips = {
        "x": _("Pie chart data\nThe fractional area of each wedge is given "
               "by x/sum(x)\nThe wedges are plotted counterclockwise"),
        "labels": _("Sequence of wedge label strings"),
        "colors": _("Sequence of matplotlib color args through which the pie "
                    "cycles.\nSupported strings are:\n'b': blue\n'g': green\n"
                    "'r': red\n'c': cyan\n'm': magenta\n'y': yellow\n'k': "
                    "black\n'w': white\nGray shades can be given as a string"
                    "that encodes a float in the 0-1 range, e.g.: '0.75'. "
                    "You can also specify the color with an html hex string "
                    "as in: '#eeefff'. Finally, legal html names for colors, "
                    "such as 'red', 'burlywood' and 'chartreuse' are "
                    "supported."),
        "startangle": _("Rotates the start of the pie chart by angle degrees "
                        "counterclockwise from the x-axis."),
        "shadow": _("If True then a shadow beneath the pie is drawn"),
    }


class AnnotateAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides annotation attributes in multiple boxed panels"""

    # Data for annotation
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "s": (_("Text"), StringEditor, ""),
        "xy": (_("Point"), StringEditor, ""),
        "xycoords": (_("Coordinates"), CoordinatesEditor, "data"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Annotation"), ["s", "xy", "xycoords"]),
    ]

    tooltips = {
        "s": _("Annotation text"),
        "xy": _("Point that is annotated"),
        "xycoords": _("String that indicates the coordinates of xy"),
        "xytext": _("Location of annotation text"),
        "textcoords": _("String that indicates the coordinates of xytext."),
    }


class ContourAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides contour attributes in multiple boxed panels"""

    # Data for contour plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "X": (_("X"), StringEditor, ""),
        "Y": (_("Y"), StringEditor, ""),
        "Z": (_("Z"), StringEditor, ""),
        "colors": (_("Colors"), StringEditor, ""),
        "alpha": (_("Alpha"), StringEditor, "1.0"),
        "linestyles": (_("Style"), LineStyleEditor, '-'),
        "linewidths": (_("Width"), IntegerEditor, "1"),
        "contour_labels": (_("Contour labels"), BoolEditor, True),
        "contour_label_fontsize": (_("Font size"), IntegerEditor, "10"),
        "contour_fill": (_("Fill contour"), BoolEditor, False),
        "hatches": (_("Hatches"), StringEditor, ""),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["X", "Y", "Z"]),
        (_("Lines"), ["linestyles", "linewidths", "colors", "alpha"]),
        (_("Areas"), ["contour_fill", "hatches"]),
        (_("Labels"), ["contour_labels", "contour_label_fontsize"]),
    ]

    tooltips = {
        "X": _("X coordinates of the surface"),
        "Y": _("Y coordinates of the surface"),
        "Z": _("Z coordinates of the surface (contour height)"),
        "colors":  _("If None, the colormap specified by cmap will be used.\n"
                     "If a string, like ‘r’ or ‘red’, all levels will be "
                     "plotted in this color.\nIf a tuple of matplotlib color "
                     "args (string, float, rgb, etc), different levels will "
                     "be plotted in different colors in the order"
                     " specified."),
        "alpha": _("The alpha blending value"),
        "linestyles": _("Contour line style"),
        "linewidths": _("All contour levels will be plotted with this "
                        "linewidth."),
        "contour_labels": _("Adds contour labels"),
        "contour_label_fontsize": _("Contour font label size in points"),
        "hatches": _("A list of cross hatch patterns to use on the filled "
                     "areas. A hatch can be one of:\n"
                     "/   - diagonal hatching\n"
                     "\   - back diagonal\n"
                     "|   - vertical\n"
                     "-   - horizontal\n"
                     "+   - crossed\n"
                     "x   - crossed diagonal\n"
                     "o   - small circle\n"
                     "O   - large circle\n"
                     ".   - dots\n"
                     "*   - stars\n"
                     "Letters can be combined, in which case all the "
                     "specified hatchings are done. If same letter repeats, "
                     "it increases the density of hatching of that pattern."),
    }


class SankeyAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides Sankey plot attributes in multiple boxed panels"""

    # Data for Sankey plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "flows": (_("Flows"), StringEditor, ""),
        "orientations": (_("Orientations"), StringEditor, ""),
        "labels": (_("Labels"), StringEditor, ""),
        "format": (_("Format"), TextEditor, "%f"),
        "unit": (_("Unit"), TextEditor, ""),
        "rotation": (_("Rotation"), IntegerEditor, "0"),
        "gap": (_("Gap"), StringEditor, "0.25"),
        "radius": (_("Radius"), StringEditor, "0.1"),
        "shoulder": (_("Shoulder"), StringEditor, "0.03"),
        "offset": (_("Offset"), StringEditor, "0.15"),
        "head_angle": (_("Angle"), IntegerEditor, "100"),
        "edgecolor": (_("Edge"), ColorEditor, "(0, 0, 1)"),
        "facecolor": (_("Face"), ColorEditor, "(0, 0, 1)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["flows", "orientations", "labels", "format", "unit"]),
        (_("Diagram"), ["rotation", "gap", "radius", "shoulder", "offset",
                        "head_angle"]),
        (_("Area"), ["edgecolor", "facecolor"]),
    ]

    tooltips = {
        "flows": _("Array of flow values.\nBy convention, inputs are positive"
                   " and outputs are negative."),
        "orientations": _("List of orientations of the paths.\nValid values "
                          "are 1 (from/to the top), 0 (from/to the left or "
                          "right), or -1 (from/to the bottom).\nIf "
                          "orientations == 0, inputs will break in from the "
                          "left and outputs will break away to the right."),
        "labels": _("List of specifications of the labels for the flows.\n"
                    "Each value may be None (no labels), ‘’ (just label the "
                    "quantities), or a labeling string. If a single value is "
                    "provided, it will be applied to all flows. If an entry "
                    "is a non-empty string, then the quantity for the "
                    "corresponding flow will be shown below the string. "
                    "However, if the unit of the main diagram is None, then "
                    "quantities are never shown, regardless of the value of "
                    "this argument."),
        "unit": _("String representing the physical unit associated with "
                  "the flow quantities.\nIf unit is None, then none of the "
                  "quantities are labeled."),
        "format": _("A Python number formatting string to be used in "
                    "labeling the flow as a quantity (i.e., a number times a "
                    "unit, where the unit is given)"),
        "rotation": _("Angle of rotation of the diagram [deg]"),
        "gap": _("Space between paths that break in/break away to/from the "
                 "top or bottom."),
        "radius": _("Inner radius of the vertical paths"),
        "shoulder": _("Size of the shoulders of output arrows"),
        "offset": _("Text offset (from the dip or tip of the arrow)"),
        "head_angle": _("Angle of the arrow heads (and negative of the angle "
                        "of the tails) [deg]"),
        "edgecolor": _("Edge color of Sankey diagram"),
        "facecolor": _("Face color of Sankey diagram"),
    }


class FigureAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides figure attributes in multiple boxed panels"""

    # strftime doc taken from Python documentation

    strftime_doc = _("""
Code 	Meaning
%a 	Locale’s abbreviated weekday name.
%A 	Locale’s full weekday name.
%b 	Locale’s abbreviated month name.
%B 	Locale’s full month name.
%c 	Locale’s appropriate date and time representation.
%d 	Day of the month as a decimal number [01,31].
%f 	Microsecond as a decimal number [0,999999], zero-padded on the left
%H 	Hour (24-hour clock) as a decimal number [00,23].
%I 	Hour (12-hour clock) as a decimal number [01,12].
%j 	Day of the year as a decimal number [001,366].
%m 	Month as a decimal number [01,12].
%M 	Minute as a decimal number [00,59].
%p 	Locale’s equivalent of either AM or PM.
%S 	Second as a decimal number [00,61].
%U 	Week number (Sunday first weekday) as a decimal number [00,53].
%w 	Weekday as a decimal number [0(Sunday),6]. 	4
%W 	Week number (Monday first weekday) as a decimal number [00,53].
%x 	Locale’s appropriate date representation.
%X 	Locale’s appropriate time representation.
%y 	Year without century as a decimal number [00,99].
%Y 	Year with century as a decimal number.
%z 	UTC offset in the form +HHMM or -HHMM.
%Z 	Time zone name.
%% 	A literal '%' character.""")

    # Data for figure
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "title": (_("Title"), TextEditor, ""),
        "xlabel": (_("Label"), TextEditor, ""),
        "xlim": (_("Limits"), StringEditor, ""),
        "xscale": (_("Log. scale"), BoolEditor, False),
        "xticks": (_("X-axis ticks"), StringEditor, ""),
        "xtick_labels": (_("X-axis labels"), TextEditor, ""),
        "xtick_params": (_("X-axis ticks"), TickParamsEditor, ""),
        "ylabel": (_("Label"), TextEditor, ""),
        "ylim": (_("Limits"), StringEditor, ""),
        "yscale": (_("Log. scale"), BoolEditor, False),
        "yticks": (_("Y-axis ticks"), StringEditor, ""),
        "ytick_labels": (_("Y-axis labels"), TextEditor, ""),
        "ytick_params": (_("Y-axis ticks"), TickParamsEditor, ""),
        "xgrid": (_("X-axis grid"), BoolEditor, False),
        "ygrid": (_("Y-axis grid"), BoolEditor, False),
        "legend": (_("Legend"), BoolEditor, False),
        "xdate_format": (_("Date format"), StringEditor, ""),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Figure"), ["title", "legend"]),
        (_("X-Axis"), ["xlabel", "xlim", "xscale", "xgrid", "xdate_format",
                       "xticks", "xtick_labels", "xtick_params"]),
        (_("Y-Axis"), ["ylabel", "ylim", "yscale", "ygrid",
                       "yticks", "ytick_labels", "ytick_params"]),
    ]

    tooltips = {
        "title": _("The figure title"),
        "xlabel": _("The label for the x axis"),
        "xlim": _("The data limits for the x axis\nFormat: (xmin, xmax)"),
        "ylabel": _("The label for the y axis"),
        "ylim": _("The data limits for the y axis\nFormat: (ymin, ymax)"),
        "xdate_format": _("If non-empty then the x axis is displays dates.\n"
                          "Enter an unquoted strftime() format string."
                          "\n") + strftime_doc,
        "xtick_labels": _("Custom labels for the x axis."),
        "ytick_labels": _("Custom labels for the y axis."),
    }


class SeriesPanel(wx.Panel):
    """Panel that holds attribute information for one series of the chart"""

    plot_types = [
        {"type": "plot", "panel_class": PlotAttributesPanel},
        {"type": "bar", "panel_class": BarAttributesPanel},
        {"type": "hist", "panel_class": HistogramAttributesPanel},
        {"type": "boxplot", "panel_class": BoxplotAttributesPanel},
        {"type": "pie", "panel_class": PieAttributesPanel},
        {"type": "annotate", "panel_class": AnnotateAttributesPanel},
        {"type": "contour", "panel_class": ContourAttributesPanel},
        {"type": "Sankey", "panel_class": SankeyAttributesPanel},
    ]

    def __init__(self, grid, series_dict):

        self.grid = grid

        wx.Panel.__init__(self, grid, -1)

        self.chart_type_book = wx.Treebook(self, -1, style=wx.BK_LEFT)
        self.il = wx.ImageList(24, 24)

        # Add plot panels

        for i, plot_type_dict in enumerate(self.plot_types):
            plot_type = plot_type_dict["type"]
            PlotPanelClass = plot_type_dict["panel_class"]

            series_data = {}
            if plot_type == series_dict["type"]:
                for key in series_dict:
                    series_data[key] = charts.object2code(key,
                                                          series_dict[key])

            plot_panel = PlotPanelClass(self.chart_type_book, series_data, -1)

            self.chart_type_book.AddPage(plot_panel, plot_type, imageId=i)
            self.il.Add(icons[plot_type_dict["type"]])

        self.plot_type = series_dict["type"]

        self._properties()
        self.__do_layout()

    def _properties(self):
        self.chart_type_book.SetImageList(self.il)

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 2, 0, 0)
        main_sizer.Add(self.chart_type_book, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(main_sizer)

        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableCol(1)

        self.Layout()

    def __iter__(self):
        """Yields all keys of current pot panel"""

        panel = self.get_plot_panel()

        # First yield the panel type because it is not contained in any widget
        chart_type_number = self.chart_type_book.GetSelection()
        chart_type = self.plot_types[chart_type_number]["type"]
        yield "type", chart_type

        for key, code in panel:
            yield key, code

    def get_plot_panel(self):
        """Returns current plot_panel"""

        plot_type_no = self.chart_type_book.GetSelection()
        return self.chart_type_book.GetPage(plot_type_no)

    def set_plot_panel(self, plot_type_no):
        """Sets current plot_panel to plot_type_no"""

        self.chart_type_book.SetSelection(plot_type_no)

    plot_panel = property(get_plot_panel, set_plot_panel)

    def get_plot_type(self):
        """Returns current plot type"""

        return self.plot_types[self.plot_panel]["type"]

    def set_plot_type(self, plot_type):
        """Sets plot type"""

        ptypes = [pt["type"] for pt in self.plot_types]
        self.plot_panel = ptypes.index(plot_type)

    plot_type = property(get_plot_type, set_plot_type)


class AllSeriesPanel(wx.Panel, ChartDialogEventMixin):
    """Panel that holds series panels for all series of the chart"""

    def __init__(self, grid):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        self.grid = grid

        self.updating = False  # Set to true if you want to delete all tabs

        wx.Panel.__init__(self, grid, style=style)

        agwstyle = fnb.FNB_NODRAG | fnb.FNB_DROPDOWN_TABS_LIST | fnb.FNB_BOTTOM
        self.series_notebook = fnb.FlatNotebook(self, -1, agwStyle=agwstyle)

        self.__bindings()
        self.__do_layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.OnSeriesChanged)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSING, self.OnSeriesDeleted)

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 1, 0, 0)

        main_sizer.Add(self.series_notebook,
                       1, wx.EXPAND | wx.FIXED_MINSIZE, 0)

        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)

        self.SetSizer(main_sizer)

        self.Layout()

    def __iter__(self):
        """Yields series panels of the chart's series"""

        no_pages = self.series_notebook.GetPageCount()
        for page_number in range(no_pages - 1):
            yield self.series_notebook.GetPage(page_number)

    def update(self, series_list):
        """Updates widget content from series_list

        Parameters
        ----------
        series_list: List of dict
        \tList of dicts with data from all series

        """

        if not series_list:
            self.series_notebook.AddPage(wx.Panel(self, -1), _("+"))
            return

        self.updating = True

        # Delete all tabs in the notebook
        self.series_notebook.DeleteAllPages()

        # Add as many tabs as there are series in code

        for page, attrdict in enumerate(series_list):
            series_panel = SeriesPanel(self.grid, attrdict)
            name = "Series"

            self.series_notebook.InsertPage(page, series_panel, name)

        self.series_notebook.AddPage(wx.Panel(self, -1), _("+"))

        self.updating = False

    # Handlers
    # --------

    def OnSeriesChanged(self, event):
        """FlatNotebook change event handler"""

        selection = event.GetSelection()

        if not self.updating and \
           selection == self.series_notebook.GetPageCount() - 1:
            # Add new series
            new_panel = SeriesPanel(self, {"type": "plot"})
            self.series_notebook.InsertPage(selection, new_panel, _("Series"))

        event.Skip()

    def OnSeriesDeleted(self, event):
        """FlatNotebook closing event handler"""

        # Redraw Chart
        post_command_event(self, self.DrawChartMsg)

        event.Skip()


class FigurePanel(wx.Panel):
    """Panel that draws a matplotlib figure_canvas"""

    def __init__(self, parent):

        wx.Panel.__init__(self, parent)
        self.__do_layout()

    def __do_layout(self):
        self.main_sizer = wx.FlexGridSizer(1, 1, 0, 0)

        self.main_sizer.AddGrowableRow(0)
        self.main_sizer.AddGrowableCol(0)

        self.SetSizer(self.main_sizer)

        self.Layout()

    def _get_figure_canvas(self, figure):
        """Returns figure canvas"""

        return FigureCanvasWxAgg(self, -1, figure)

    def update(self, figure):
        """Updates figure on data change

        Parameters
        ----------
        * figure: matplotlib.figure.Figure
        \tMatplotlib figure object that is displayed in self

        """

        if hasattr(self, "figure_canvas"):
            self.figure_canvas.Destroy()

        self.figure_canvas = self._get_figure_canvas(figure)

        self.figure_canvas.SetSize(self.GetSize())
        figure.subplots_adjust()

        self.main_sizer.Add(self.figure_canvas, 1,
                            wx.EXPAND | wx.FIXED_MINSIZE, 0)

        self.Layout()
        self.figure_canvas.draw()


class ChartDialog(wx.Dialog, ChartDialogEventMixin):
    """Chart dialog for generating chart generation strings"""

    def __init__(self, main_window, key, code):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME
        wx.Dialog.__init__(self, main_window, -1, style=style)

        self.updating = False

        self.grid = main_window.grid
        self.key = key

        self.figure_attributes_panel = FigureAttributesPanel(self, {}, -1)
        self.all_series_panel = AllSeriesPanel(self)
        self.figure_panel = FigurePanel(self)

        # Figure cache speeds up screen updates if figure code is unchanged
        self.figure_code_old = None
        self.figure_cache = None

        self.cancel_button = wx.Button(self, wx.ID_CANCEL)
        self.ok_button = wx.Button(self, wx.ID_OK)

        # The code has to be set after all widgets are created
        self.code = code

        self.__set_properties()
        self.__do_layout()
        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(self.EVT_CMD_DRAW_CHART, self.OnUpdateFigurePanel)

    def __set_properties(self):
        self.SetTitle(_("Insert chart"))

        self.figure_attributes_staticbox = wx.StaticBox(self, -1, _("Axes"))
        self.series_staticbox = wx.StaticBox(self, -1, _("Series"))

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(2, 1, 2, 2)
        chart_sizer = wx.FlexGridSizer(1, 3, 2, 2)
        figure_attributes_box_sizer = \
            wx.StaticBoxSizer(self.figure_attributes_staticbox, wx.HORIZONTAL)
        series_box_sizer = \
            wx.StaticBoxSizer(self.series_staticbox, wx.VERTICAL)
        button_sizer = wx.FlexGridSizer(1, 3, 0, 3)

        main_sizer.Add(chart_sizer, 1, wx.EXPAND, 0)
        main_sizer.Add(button_sizer, 1, wx.FIXED_MINSIZE, 0)

        chart_sizer.Add(figure_attributes_box_sizer, 1, wx.EXPAND, 0)
        chart_sizer.Add(series_box_sizer, 1, wx.EXPAND, 0)
        chart_sizer.Add(self.figure_panel, 1, wx.EXPAND, 0)

        main_sizer.SetMinSize((1000, -1))
        main_sizer.SetFlexibleDirection(wx.BOTH)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        try:
            main_sizer.RemoveGrowableRow(1)
        except:
            pass

        chart_sizer.SetMinSize((1000, -1))
        chart_sizer.AddGrowableRow(0)

        if wx.version().startswith("2."):
            chart_sizer.AddGrowableCol(0, proportion=1)
            chart_sizer.AddGrowableCol(1, proportion=1)
            chart_sizer.AddGrowableCol(2, proportion=1)
        else:
            # wxPython3 has changed widow layout
            chart_sizer.AddGrowableCol(0, proportion=0.5)
            chart_sizer.AddGrowableCol(1, proportion=2)
            chart_sizer.AddGrowableCol(2, proportion=2)

        figure_attributes_box_sizer.Add(self.figure_attributes_panel,
                                        1, wx.EXPAND, 0)
        series_box_sizer.Add(self.all_series_panel, 1, wx.EXPAND, 0)

        style = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL
        button_sizer.Add(self.ok_button, 0, style, 3)
        button_sizer.Add(self.cancel_button, 0, style, 3)
        button_sizer.AddGrowableCol(2)

        self.Layout()
        self.SetSizerAndFit(main_sizer)

    def get_figure(self, code):
        """Returns figure from executing code in grid

        Returns an empty matplotlib figure if code does not eval to a
        matplotlib figure instance.

        Parameters
        ----------
        code: Unicode
        \tUnicode string which contains Python code that should yield a figure

        """

        # Caching for fast response if there are no changes
        if code == self.figure_code_old and self.figure_cache:
            return self.figure_cache

        self.figure_code_old = code

        # key is the current cursor cell of the grid
        key = self.grid.actions.cursor
        cell_result = self.grid.code_array._eval_cell(key, code)

        # If cell_result is matplotlib figure
        if isinstance(cell_result, matplotlib.pyplot.Figure):
            # Return it
            self.figure_cache = cell_result
            return cell_result

        else:
            # Otherwise return empty figure
            self.figure_cache = charts.ChartFigure()

        return self.figure_cache

    # Tuple keys have to be put in parentheses
    tuple_keys = ["xdata", "ydata", "left", "height", "width", "bottom",
                  "xlim", "ylim", "x", "labels", "colors", "xy", "xytext",
                  "title", "xlabel", "ylabel", "label", "X", "Y", "Z",
                  "hatches", "flows", "orientations", "labels"]

    # String keys need to be put in "
    string_keys = ["type", "linestyle", "marker", "shadow", "vert", "xgrid",
                   "ygrid", "notch", "sym", "normed", "cumulative",
                   "xdate_format", "xycoords", "textcoords", "linestyles",
                   "contour_labels", "contour_fill", "format", "unit"]

    # Keys, which have to be None if empty
    empty_none_keys = ["colors", "color"]

    def set_code(self, code):
        """Update widgets from code"""

        # Get attributes from code

        attributes = []
        strip = lambda s: s.strip('u').strip("'").strip('"')
        for attr_dict in parse_dict_strings(str(code).strip()[19:-1]):
            attrs = list(strip(s) for s in parse_dict_strings(attr_dict[1:-1]))
            attributes.append(dict(list(zip(attrs[::2], attrs[1::2]))))

        if not attributes:
            return

        # Set widgets from attributes
        # ---------------------------

        # Figure attributes
        figure_attributes = attributes[0]

        for key, widget in self.figure_attributes_panel:
            try:
                obj = figure_attributes[key]
                kwargs_key = key + "_kwargs"
                if kwargs_key in figure_attributes:
                    widget.set_kwargs(figure_attributes[kwargs_key])

            except KeyError:
                obj = ""

            widget.code = charts.object2code(key, obj)

        # Series attributes
        self.all_series_panel.update(attributes[1:])

    def get_code(self):
        """Returns code that generates figure from widgets"""

        def dict2str(attr_dict):
            """Returns string with dict content with values as code

            Code means that string identifiers are removed

            """

            result = "{"

            for key in attr_dict:
                code = attr_dict[key]

                if key in self.string_keys:
                    code = repr(code)

                elif code and key in self.tuple_keys and \
                     not (code[0] in ["[", "("] and code[-1] in ["]", ")"]):

                    code = "(" + code + ")"

                elif key in ["xscale", "yscale"]:
                    if code:
                        code = '"log"'
                    else:
                        code = '"linear"'

                elif key in ["legend"]:
                    if code:
                        code = '1'
                    else:
                        code = '0'

                elif key in ["xtick_params"]:
                    code = '"x"'

                elif key in ["ytick_params"]:
                    code = '"y"'

                if not code:
                    if key in self.empty_none_keys:
                        code = "None"
                    else:
                        code = 'u""'

                result += repr(key) + ": " + code + ", "

            result = result[:-2] + "}"

            return result

        # cls_name inludes full class name incl. charts
        cls_name = "charts." + charts.ChartFigure.__name__

        attr_dicts = []

        # Figure attributes
        attr_dict = {}
        # figure_attributes is a dict key2code
        for key, widget in self.figure_attributes_panel:
            if key == "type":
                attr_dict[key] = widget
            else:
                attr_dict[key] = widget.code
                try:
                    attr_dict[key+"_kwargs"] = widget.get_kwargs()
                except AttributeError:
                    pass

        attr_dicts.append(attr_dict)

        # Series_attributes is a list of dicts key2code
        for series_panel in self.all_series_panel:
            attr_dict = {}
            for key, widget in series_panel:
                if key == "type":
                    attr_dict[key] = widget
                else:
                    attr_dict[key] = widget.code

            attr_dicts.append(attr_dict)

        code = cls_name + "("

        for attr_dict in attr_dicts:
            code += dict2str(attr_dict) + ", "

        code = code[:-2] + ")"

        return code

    # Properties
    # ----------

    code = property(get_code, set_code)

    # Handlers
    # --------

    def OnUpdateFigurePanel(self, event):
        """Redraw event handler for the figure panel"""

        if self.updating:
            return

        self.updating = True
        self.figure_panel.update(self.get_figure(self.code))
        self.updating = False

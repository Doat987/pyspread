#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# xlspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# xlspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with xlspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

xls
===

This file contains interfaces to Excel xls file format.

"""

from copy import copy
from collections import defaultdict
from datetime import datetime
from itertools import product, repeat

try:
    import xlrd

except ImportError:
    xlrd = None

try:
    import xlwt

except ImportError:
    xlwt = None

import wx

import src.lib.i18n as i18n

from src.lib.selection import Selection

from src.sysvars import get_dpi, get_default_text_extent, get_color

from src.config import config


from gettext import gettext as _


class Xls(object):
    """Interface between code_array and xls file

    The xls file is read from disk with the read method.
    The xls file is written to disk with the write method.

    Parameters
    ----------

    code_array: model.CodeArray object
    \tThe code_array object data structure
    workbook: xlrd Workbook object
    \tFile like object in xls format

    """

    def __init__(self, code_array, workbook):
        self.code_array = code_array
        self.workbook = workbook

        self.xls_max_rows = 65536
        self.xls_max_cols = 256
        self.xls_max_tabs = 256  # Limit tables to 255 to avoid cluttered Excel

    def idx2colour(self, idx):
        """Returns wx.Colour"""

        return wx.Colour(*self.workbook.colour_map[idx])

    def color2idx(self, red, green, blue):
        """Get an Excel index from"""

        xlwt_colors = [
            (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255), (0, 0, 0),
            (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255), (128, 0, 0),
            (0, 128, 0), (0, 0, 128), (128, 128, 0), (128, 0, 128),
            (0, 128, 128), (192, 192, 192), (128, 128, 128), (153, 153, 255),
            (153, 51, 102), (255, 255, 204), (204, 255, 255), (102, 0, 102),
            (255, 128, 128), (0, 102, 204), (204, 204, 255), (0, 0, 128),
            (255, 0, 255), (255, 255, 0), (0, 255, 255), (128, 0, 128),
            (128, 0, 0), (0, 128, 128), (0, 0, 255), (0, 204, 255),
            (204, 255, 255), (204, 255, 204), (255, 255, 153), (153, 204, 255),
            (255, 153, 204), (204, 153, 255), (255, 204, 153), (51, 102, 255),
            (51, 204, 204), (153, 204, 0), (255, 204, 0), (255, 153, 0),
            (255, 102, 0), (102, 102, 153), (150, 150, 150), (0, 51, 102),
            (51, 153, 102), (0, 51, 0), (51, 51, 0), (153, 51, 0),
            (153, 51, 102), (51, 51, 153), (51, 51, 51)
        ]

        distances = [abs(red - r) + abs(green - g) + abs(blue - b)
                     for r, g, b in xlwt_colors]

        min_dist_idx = distances.index(min(distances))

        return min_dist_idx

    def _shape2xls(self, worksheets):
        """Writes shape to xls file

        Format: <rows>\t<cols>\t<tabs>\n

        """

        __, __, tabs = self.code_array.shape

        if tabs > self.xls_max_tabs:
            tabs = self.xls_max_tabs

        for tab in range(tabs):
            worksheet = self.workbook.add_sheet(str(tab))
            worksheets.append(worksheet)

    def _xls2shape(self):
        """Updates shape in code_array"""

        sheets = self.workbook.sheets()
        nrows = 1
        ncols = 1
        for sheet in sheets:
            nrows = max(nrows, sheet.nrows)
            ncols = max(ncols, sheet.ncols)
        ntabs = len(sheets)

        self.code_array.shape = nrows, ncols, ntabs

    def _code2xls(self, worksheets):
        """Writes code to xls file

        Format: <row>\t<col>\t<tab>\t<code>\n

        """

        code_array = self.code_array

        xls_max_shape = self.xls_max_rows, self.xls_max_cols, self.xls_max_tabs

        for key in code_array:
            if all(kele < mele for kele, mele in zip(key, xls_max_shape)):
                # Cell lies within Excel boundaries
                row, col, tab = key
                code_str = code_array(key)
                style = self._get_xfstyle(worksheets, key)
                worksheets[tab].write(row, col, label=code_str, style=style)

        # Handle cell formatting in cells without code

        # Get bboxes for all cell_attributes
        max_shape = [min(xls_max_shape[0], code_array.shape[0]),
                     min(xls_max_shape[1], code_array.shape[1])]

        # Prevent systems from blocking
        if max_shape[0] * max_shape[1] > 1024000:
            # Ignore all cell attributes below row 3999
            max_shape[0] = 4000

        cell_attributes = code_array.dict_grid.cell_attributes
        bboxes = []
        for s, __tab, __ in cell_attributes:
            if s:
                bboxes.append((s.get_grid_bbox(code_array.shape), __tab))

        # Get bbox_cell_set from bboxes
        cells = []
        for ((bb_top, bb_left), (bb_bottom, bb_right)), __tab in bboxes:
            __bb_bottom = min(bb_bottom, max_shape[0])
            __bb_right = min(bb_right, max_shape[1])
            for __row, __col in product(range(bb_top, __bb_bottom + 1),
                                        range(bb_left, __bb_right + 1)):
                cells.append((__row, __col, __tab))

        cell_set = set(cells)
        # Loop over those with non-standard attributes
        for key in cell_set:
            if key not in code_array and all(ele >= 0 for ele in key):
                row, col, tab = key
                style = self._get_xfstyle(worksheets, key)
                worksheets[tab].write(row, col, label="", style=style)

    def _xls2code(self, worksheet, tab):
        """Updates code in xls code_array"""

        def xlrddate2datetime(xlrd_date):
            """Returns datetime from xlrd_date"""

            try:
                xldate_tuple = xlrd.xldate_as_tuple(xlrd_date,
                                                    self.workbook.datemode)
                return datetime(xldate_tuple)

            except (ValueError, TypeError):
                return ''

        type2mapper = {
            0: lambda x: None,  # Empty cell
            1: lambda x: str(x),  # Text cell
            2: lambda x: str(x),  # Number cell
            3: xlrddate2datetime,  # Date
            4: lambda x: str(bool(x)),  # Boolean cell
            5: lambda x: str(x),  # Error cell
            6: lambda x: None,  # Blank cell
        }

        rows, cols = worksheet.nrows, worksheet.ncols
        for row, col in product(range(rows), range(cols)):
            cell_type = worksheet.cell_type(row, col)
            cell_value = worksheet.cell_value(row, col)

            key = row, col, tab
            mapper = type2mapper[cell_type]
            self.code_array[key] = mapper(cell_value)

    def _get_font(self, pys_style):
        """Returns xlwt.Font for pyspread style"""

        # Return None if there is no font
        if "textfont" not in pys_style:
            return

        font = xlwt.Font()

        font.name = pys_style["textfont"]

        if "pointsize" in pys_style:
            font.height = pys_style["pointsize"] * 20.0

        if "fontweight" in pys_style:
            font.bold = (pys_style["fontweight"] == wx.BOLD)

        if "fontstyle" in pys_style:
            font.italic = (pys_style["fontstyle"] == wx.ITALIC)

        if "textcolor" in pys_style:
            textcolor = wx.Colour()
            textcolor.SetRGB(pys_style["textcolor"])
            font.colour_index = self.color2idx(*textcolor.Get())

        if "underline" in pys_style:
            font.underline_type = pys_style["underline"]

        if "strikethrough" in pys_style:
            font.struck_out = pys_style["strikethrough"]

        return font

    def _get_alignment(self, pys_style):
        """Returns xlwt.Alignment for pyspread style"""

        # Return None if there is no alignment
        alignment_styles = ["justification", "vertical_align", "angle"]
        if not any(astyle in pys_style for astyle in alignment_styles):
            return

        def angle2xfrotation(angle):
            """Returns angle from xlrotatation"""

            # angle is counterclockwise
            if 0 <= angle <= 90:
                return angle

            elif -90 <= angle < 0:
                return 90 - angle

            return 0

        justification2xfalign = {
            "left": 1,
            "center": 2,
            "right": 3,
        }

        vertical_align2xfalign = {
            "top": 0,
            "middle": 1,
            "bottom": 2,
        }

        alignment = xlwt.Alignment()

        try:
            alignment.horz = justification2xfalign[pys_style["justification"]]

        except KeyError:
            pass

        try:
            alignment.vert = \
                vertical_align2xfalign[pys_style["vertical_align"]]

        except KeyError:
            pass

        try:
            alignment.rota = angle2xfrotation(pys_style["angle"])

        except KeyError:
            pass

        return alignment

    def _get_pattern(self, pys_style):
        """Returns xlwt.pattern for pyspread style"""

        # Return None if there is no bgcolor
        if "bgcolor" not in pys_style:
            return

        pattern = xlwt.Pattern()
        pattern.pattern = xlwt.Pattern.SOLID_PATTERN

        bgcolor = wx.Colour()
        bgcolor.SetRGB(pys_style["bgcolor"])
        pattern.pattern_fore_colour = self.color2idx(*bgcolor.Get())

        return pattern

    def _get_borders(self, pys_style, pys_style_above, pys_style_left):
        """Returns xlwt.Borders for pyspread style"""

        # Return None if there is no border key
        border_keys = [
            "borderwidth_right",
            "borderwidth_bottom",
            "bordercolor_right",
            "bordercolor_bottom",
        ]

        if not any(border_key in pys_style for border_key in border_keys):
            return

        def width2border_line_style(width):
            if width == 0:
                return xlwt.Borders.NO_LINE

            if 0 < width < 2:
                return xlwt.Borders.THIN

            if 2 <= width < 6:
                return xlwt.Borders.MEDIUM

            if width >= 6:
                return xlwt.Borders.THICK

            raise ValueError("Width {} unknown".format(width))

        DEFAULT_LINE_STYLE = xlwt.Borders.THIN
        DEFAULT_COLOR_IDX = 0x16  # Tried out with gnumeric and LibreOffice

        borders = xlwt.Borders()

        # Width / style
        # -------------

        # Bottom width

        try:
            bottom_pys_style = pys_style["borderwidth_bottom"]
            bottom_line_style = width2border_line_style(bottom_pys_style)

        except KeyError:
            # No or unknown border width
            bottom_line_style = DEFAULT_LINE_STYLE

        finally:
            borders.bottom = bottom_line_style

        # Right width

        try:
            right_pys_style = pys_style["borderwidth_right"]
            right_line_style = width2border_line_style(right_pys_style)

        except KeyError:
            # No or unknown border width
            right_line_style = DEFAULT_LINE_STYLE

        finally:
            borders.right = right_line_style

        # Top width

        try:
            top_pys_style = pys_style_above["borderwidth_bottom"]
            top_line_style = width2border_line_style(top_pys_style)

        except KeyError:
            # No or unknown border width
            top_line_style = DEFAULT_LINE_STYLE

        finally:
            borders.top = top_line_style

        # Left width

        try:
            left_pys_style = pys_style_left["borderwidth_right"]
            left_line_style = width2border_line_style(left_pys_style)

        except KeyError:
            # No or unknown border width
            left_line_style = DEFAULT_LINE_STYLE

        finally:
            borders.left = left_line_style

        # Border colors
        # -------------

        # Bottom color

        def _get_color_idx(color):
            """Converts wx.Colour to Excel color index

            Differs from self.color2idx because it maps
            the pyspread default grid color to the Excel default color

            Parameters
            ----------
            color: wx.Colour
            \tColor to be converted

            """

            if color == get_color(config["grid_color"]):
                return DEFAULT_COLOR_IDX
            else:
                return self.color2idx(*color.Get())

        try:
            bottom_color_pys_style = pys_style["bordercolor_bottom"]
            bcolor = wx.Colour()
            bcolor.SetRGB(bottom_color_pys_style)
            bottom_color_idx = _get_color_idx(bcolor)

        except KeyError:
            # No or unknown border color
            bottom_color_idx = DEFAULT_COLOR_IDX

        finally:
            borders.bottom_colour = bottom_color_idx

        # Right color

        try:
            right_color_pys_style = pys_style["bordercolor_right"]
            rcolor = wx.Colour()
            rcolor.SetRGB(right_color_pys_style)
            right_colour_idx = _get_color_idx(rcolor)

        except KeyError:
            # No or unknown border color
            right_colour_idx = DEFAULT_COLOR_IDX

        finally:
            borders.right_colour = right_colour_idx

        # Top color

        try:
            top_color_pys_style = pys_style_above["bordercolor_bottom"]
            tcolor = wx.Colour()
            tcolor.SetRGB(top_color_pys_style)
            top_color_idx = _get_color_idx(tcolor)

        except KeyError:
            # No or unknown border color
            top_color_idx = DEFAULT_COLOR_IDX

        finally:
            borders.top_colour = top_color_idx

        # Left color

        try:
            left_color_pys_style = pys_style_left["bordercolor_right"]
            lcolor = wx.Colour()
            lcolor.SetRGB(left_color_pys_style)
            left_colour_idx = _get_color_idx(lcolor)

        except KeyError:
            # No or unknown border color
            left_colour_idx = DEFAULT_COLOR_IDX

        finally:
            borders.left_colour = left_colour_idx

        return borders

    def _get_xfstyle(self, worksheets, key):
        """Gets XFStyle for cell key"""

        row, col, tab = key
        dict_grid = self.code_array.dict_grid

        pys_style = dict_grid.cell_attributes[key]
        pys_style_above = dict_grid.cell_attributes[row - 1, col, tab]
        pys_style_left = dict_grid.cell_attributes[row, col - 1, tab]

        xfstyle = xlwt.XFStyle()

        # Font
        # ----

        font = self._get_font(pys_style)
        if font is not None:
            xfstyle.font = font

        # Alignment
        # ---------

        alignment = self._get_alignment(pys_style)
        if alignment is not None:
            xfstyle.alignment = alignment

        # Background / pattern
        # --------------------

        pattern = self._get_pattern(pys_style)
        if pattern is not None:
            xfstyle.pattern = pattern

        # Border
        # ------

        borders = self._get_borders(pys_style, pys_style_above, pys_style_left)
        if borders is not None:
            xfstyle.borders = borders

        return xfstyle

    def _cell_attribute_append(self, selection, tab, attributes):
        """Appends to cell_attributes with checks"""

        cell_attributes = self.code_array.cell_attributes

        thick_bottom_cells = []
        thick_right_cells = []

        # Does any cell in selection.cells have a larger bottom border?

        if "borderwidth_bottom" in attributes:
            bwidth = attributes["borderwidth_bottom"]
            for row, col in selection.cells:
                __bwidth = cell_attributes[row, col, tab]["borderwidth_bottom"]
                if __bwidth > bwidth:
                    thick_bottom_cells.append((row, col))

        # Does any cell in selection.cells have a larger right border?
        if "borderwidth_right" in attributes:
            rwidth = attributes["borderwidth_right"]
            for row, col in selection.cells:
                __rwidth = cell_attributes[row, col, tab]["borderwidth_right"]
                if __rwidth > rwidth:
                    thick_right_cells.append((row, col))

        for thick_cell in thick_bottom_cells + thick_right_cells:
            try:
                selection.cells.remove(thick_cell)
            except ValueError:
                pass

        cell_attributes.append((selection, tab, attributes))

        if thick_bottom_cells:
            bsel = copy(selection)
            bsel.cells = thick_bottom_cells
            battrs = copy(attributes)
            battrs.pop("borderwidth_bottom")
            cell_attributes.append((bsel, tab, battrs))

        if thick_right_cells:
            rsel = copy(selection)
            rsel.cells = thick_right_cells
            rattrs = copy(attributes)
            rattrs.pop("borderwidth_right")
            cell_attributes.append((rsel, tab, rattrs))

    def _xls2attributes(self, worksheet, tab):
        """Updates attributes in code_array"""

        # Merged cells
        for top, bottom, left, right in worksheet.merged_cells:
            attrs = {"merge_area": (top, left, bottom - 1, right - 1)}
            selection = Selection([(top, left)], [(bottom - 1, right - 1)],
                                  [], [], [])
            self.code_array.cell_attributes.append((selection, tab, attrs))

        # Which cell comprise which format ids
        xf2cell = dict((xfid, []) for xfid in range(self.workbook.xfcount))
        rows, cols = worksheet.nrows, worksheet.ncols
        for row, col in product(range(rows), range(cols)):
            xfid = worksheet.cell_xf_index(row, col)
            xf2cell[xfid].append((row, col))

        for xfid, xf in enumerate(self.workbook.xf_list):
            selection = Selection([], [], [], [], xf2cell[xfid])
            selection_above = selection.shifted(-1, 0)
            selection_left = selection.shifted(0, -1)

            attributes = {}

            # Alignment

            xfalign2justification = {
                0: "left",
                1: "left",
                2: "center",
                3: "right",
                4: "left",
                5: "left",
                6: "center",
                7: "left",
            }

            xfalign2vertical_align = {
                0: "top",
                1: "middle",
                2: "bottom",
                3: "middle",
                4: "middle",
            }

            def xfrotation2angle(xfrotation):
                """Returns angle from xlrotatation"""

                # angle is counterclockwise
                if 0 <= xfrotation <= 90:
                    return xfrotation

                elif 90 < xfrotation <= 180:
                    return - (xfrotation - 90)

                return 0

            try:
                attributes["justification"] = \
                    xfalign2justification[xf.alignment.hor_align]

                attributes["vertical_align"] = \
                    xfalign2vertical_align[xf.alignment.vert_align]

                attributes["angle"] = \
                    xfrotation2angle(xf.alignment.rotation)

            except AttributeError:
                pass

            # Background
            if xf.background.fill_pattern == 1:
                color_idx = xf.background.pattern_colour_index
                color = self.idx2colour(color_idx)
                attributes["bgcolor"] = color.GetRGB()

            # Border
            __border_line_style2width = {
                0: 1,
                1: 1,
                2: 4,
                5: 7,
            }

            def constant_factory(value):
                return repeat(value).__next__

            border_line_style2width = defaultdict(constant_factory(1))
            border_line_style2width.update(__border_line_style2width)

            bottom_color_idx = xf.border.bottom_colour_index

            if bottom_color_idx in self.workbook.colour_map and \
               self.workbook.colour_map[bottom_color_idx] is not None:
                bottom_color = self.idx2colour(bottom_color_idx)
                attributes["bordercolor_bottom"] = bottom_color.GetRGB()

            right_color_idx = xf.border.right_colour_index
            if right_color_idx in self.workbook.colour_map and \
               self.workbook.colour_map[right_color_idx] is not None:
                right_color = self.idx2colour(right_color_idx)
                attributes["bordercolor_right"] = right_color.GetRGB()

            bottom_width = border_line_style2width[xf.border.bottom_line_style]
            attributes["borderwidth_bottom"] = bottom_width

            right_width = border_line_style2width[xf.border.right_line_style]
            attributes["borderwidth_right"] = right_width

            # Font

            font = self.workbook.font_list[xf.font_index]

            attributes["textfont"] = font.name
            attributes["pointsize"] = font.height / 20.0

            fontweight = wx.BOLD if font.weight == 700 else wx.NORMAL
            attributes["fontweight"] = fontweight

            if font.italic:
                attributes["fontstyle"] = wx.ITALIC

            if font.colour_index in self.workbook.colour_map and \
               self.workbook.colour_map[font.colour_index] is not None:
                attributes["textcolor"] = \
                    self.idx2colour(font.colour_index).GetRGB()

            if font.underline_type:
                attributes["underline"] = True

            if font.struck_out:
                attributes["strikethrough"] = True

            # Handle top cells' top borders

            attributes_above = {}
            top_width = border_line_style2width[xf.border.top_line_style]
            if top_width != 1:
                attributes_above["borderwidth_bottom"] = top_width
            top_color_idx = xf.border.top_colour_index
            if top_color_idx in self.workbook.colour_map and \
               self.workbook.colour_map[top_color_idx] is not None:
                top_color = self.idx2colour(top_color_idx)
                attributes_above["bordercolor_bottom"] = top_color.GetRGB()

            # Handle leftmost cells' left borders

            attributes_left = {}
            left_width = border_line_style2width[xf.border.left_line_style]
            if left_width != 1:
                attributes_left["borderwidth_right"] = left_width
            left_color_idx = xf.border.left_colour_index
            if left_color_idx in self.workbook.colour_map and \
               self.workbook.colour_map[left_color_idx] is not None:
                left_color = self.idx2colour(left_color_idx)
                attributes_above["bordercolor_right"] = left_color.GetRGB()

            if attributes_above:
                self._cell_attribute_append(selection_above, tab,
                                            attributes_above)
            if attributes_left:
                self._cell_attribute_append(selection_left, tab,
                                            attributes_left)
            if attributes:
                self._cell_attribute_append(selection, tab, attributes)

    def _row_heights2xls(self, worksheets):
        """Writes row_heights to xls file

        Format: <row>\t<tab>\t<value>\n

        """

        xls_max_rows, xls_max_tabs = self.xls_max_rows, self.xls_max_tabs

        dict_grid = self.code_array.dict_grid

        for row, tab in dict_grid.row_heights:
            if row < xls_max_rows and tab < xls_max_tabs:
                height_pixels = dict_grid.row_heights[(row, tab)]
                height_inches = height_pixels / float(get_dpi()[1])
                height_points = height_inches * 72.0

                worksheets[tab].row(row).height_mismatch = True
                worksheets[tab].row(row).height = int(height_points * 20.0)

    def _xls2row_heights(self, worksheet, tab):
        """Updates row_heights in code_array"""

        for row in range(worksheet.nrows):
            try:
                height_points = worksheet.rowinfo_map[row].height / 20.0
                height_inches = height_points / 72.0
                height_pixels = height_inches * get_dpi()[1]

                self.code_array.row_heights[row, tab] = height_pixels

            except KeyError:
                pass

    def _col_widths2xls(self, worksheets):
        """Writes col_widths to xls file

        Format: <col>\t<tab>\t<value>\n

        """

        xls_max_cols, xls_max_tabs = self.xls_max_cols, self.xls_max_tabs

        dict_grid = self.code_array.dict_grid

        for col, tab in dict_grid.col_widths:
            if col < xls_max_cols and tab < xls_max_tabs:
                width_0 = get_default_text_extent("0")[0]
                width_pixels = dict_grid.col_widths[(col, tab)]
                width_0_char = width_pixels * 1.2 / width_0

                worksheets[tab].col(col).width_mismatch = True
                worksheets[tab].col(col).width = int(width_0_char * 256.0)

    def _xls2col_widths(self, worksheet, tab):
        """Updates col_widths in code_array"""

        for col in range(worksheet.ncols):
            try:
                width_0_char = worksheet.colinfo_map[col].width / 256.0
                width_0 = get_default_text_extent("0")[0]
                # Scale relative to 10 point font instead of 12 point
                width_pixels = width_0_char * width_0 / 1.2

                self.code_array.col_widths[col, tab] = width_pixels

            except KeyError:
                pass

    # Access via model.py data
    # ------------------------

    def from_code_array(self):
        """Returns xls workbook object with everything from code_array"""

        worksheets = []
        self._shape2xls(worksheets)

        self._code2xls(worksheets)

        self._row_heights2xls(worksheets)
        self._col_widths2xls(worksheets)

        return self.workbook

    def to_code_array(self):
        """Replaces everything in code_array from xls_file"""

        self._xls2shape()

        worksheets = self.workbook.sheet_names()

        for tab, worksheet_name in enumerate(worksheets):
            worksheet = self.workbook.sheet_by_name(worksheet_name)
            self._xls2code(worksheet, tab)
            self._xls2attributes(worksheet, tab)
            self._xls2row_heights(worksheet, tab)
            self._xls2col_widths(worksheet, tab)

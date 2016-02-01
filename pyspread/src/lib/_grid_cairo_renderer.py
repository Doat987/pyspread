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
_grid_cairo_renderer.py
=======================

Provides
--------

 * GridCairoRenderer: Renders grid slice to Cairo context
 * GridCellCairoRenderer: Renders grid cell to Cairo context
 * GridCellContentCairoRenderer: Renders cell content to Cairo context
 * GridCellBackgroundCairoRenderer: Renders cell background to Cairo context
 * GridCellBorderCairoRenderer: Renders cell border to Cairo context

"""

import math
import sys
import warnings
from operator import attrgetter

import cairo
import numpy
import wx
import wx.lib.wxcairo


try:
    import matplotlib.pyplot as pyplot
    from matplotlib.backends.backend_cairo import RendererCairo
    from matplotlib.backends.backend_cairo import FigureCanvasCairo
    from matplotlib.transforms import Affine2D
except ImportError:
    pyplot = None

from gi.repository import Pango as pango
from gi.repository import PangoCairo as pangocairo

from src.lib.parsers import color_pack2rgb, is_svg


STANDARD_ROW_HEIGHT = 20
STANDARD_COL_WIDTH = 50

try:
    from src.config import config
    MAX_RESULT_LENGTH = config["max_result_length"]
except ImportError:
    MAX_RESULT_LENGTH = 100000


class GridCairoRenderer(object):
    """Renders a grid slice to a CairoSurface

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * row_tb: 2 tuple of Integer
    \tStart and stop of row range with step 1
    * col_lr: 2 tuple of Integer
    \tStart and stop of col range with step 1
    * tab_fl: 2 tuple of Integer
    \tStart and stop of tab range with step 1
    * width: Float
    \tPage width in points
    * height: Float
    \tPage height in points
    * orientation: String in ["portrait", "landscape"]
    \tPage orientation
    * x_offset: Float, defaults to 20.5
    \t X offset from bage border in points
    * y_offset: Float, defaults to 20.5
    \t Y offset from bage border in points

    """

    def __init__(self, context, code_array, row_tb, col_rl, tab_fl,
                 width, height, orientation, x_offset=20.5, y_offset=20.5,
                 view_frozen=False):
        self.context = context
        self.code_array = code_array

        self.row_tb = row_tb
        self.col_rl = col_rl
        self.tab_fl = tab_fl

        self.width = width
        self.height = height

        self.x_offset = x_offset
        self.y_offset = y_offset

        self.orientation = orientation

        self.view_frozen = view_frozen

    def get_cell_rect(self, row, col, tab):
        """Returns rectangle of cell on canvas"""

        top_row = self.row_tb[0]
        left_col = self.col_rl[0]

        pos_x = self.x_offset
        pos_y = self.y_offset

        merge_area = self._get_merge_area((row, col, tab))

        for __row in range(top_row, row):
            __row_height = self.code_array.get_row_height(__row, tab)
            pos_y += __row_height

        for __col in range(left_col, col):
            __col_width = self.code_array.get_col_width(__col, tab)
            pos_x += __col_width

        if merge_area is None:
            height = self.code_array.get_row_height(row, tab)
            width = self.code_array.get_col_width(col, tab)
        else:
            # We have a merged cell
            top, left, bottom, right = merge_area
            # Are we drawing the top left cell?
            if top == row and left == col:
                # Set rect to merge area
                heights = (self.code_array.get_row_height(__row, tab)
                           for __row in range(top, bottom+1))
                widths = (self.code_array.get_col_width(__col, tab)
                          for __col in range(left, right+1))
                height = sum(heights)
                width = sum(widths)
            else:
                # Do not draw the cell because it is hidden
                return

        return pos_x, pos_y, width, height

    def _get_merge_area(self, key):
        """Returns the merge area of a merged cell

        Merge area is a 4 tuple (top, left, bottom, right)

        """

        cell_attributes = self.code_array.cell_attributes[key]
        return cell_attributes["merge_area"]

    def draw(self):
        """Draws slice to context"""

        row_start, row_stop = self.row_tb
        col_start, col_stop = self.col_rl
        tab_start, tab_stop = self.tab_fl

        for tab in range(tab_start, tab_stop):
            # Scale context to page extent
            # In order to keep the aspect ration intact use the maximum
            first_key = row_start, col_start, tab
            first_rect = self.get_cell_rect(*first_key)

            # If we have a merged cell then use the top left cell rect
            if first_rect is None:
                top, left, __, __ = self._get_merge_area(first_key)
                first_rect = self.get_cell_rect(top, left, tab)

            last_key = row_stop - 1, col_stop - 1, tab
            last_rect = self.get_cell_rect(*last_key)

            # If we have a merged cell then use the top left cell rect
            if last_rect is None:
                top, left, __, __ = self._get_merge_area(last_key)
                last_rect = self.get_cell_rect(top, left, tab)

            x_extent = last_rect[0] + last_rect[2] - first_rect[0]
            y_extent = last_rect[1] + last_rect[3] - first_rect[1]

            scale_x = (self.width - 2 * self.x_offset) / float(x_extent)
            scale_y = (self.height - 2 * self.y_offset) / float(y_extent)

            self.context.save()
            # Translate offset to o
            self.context.translate(first_rect[0], first_rect[1])

            # Scale to fit page, do not change aspect ratio
            scale = min(scale_x, scale_y)
            self.context.scale(scale, scale)

            # Translate offset
            self.context.translate(-self.x_offset, -self.y_offset)

            # TODO: Center the grid on the page

            # Render cells

            for row in range(row_start, row_stop):
                for col in range(col_start, col_stop):
                    key = row, col, tab
                    rect = self.get_cell_rect(row, col, tab)  # Rect
                    if rect is not None:
                        cell_renderer = GridCellCairoRenderer(
                            self.context,
                            self.code_array,
                            key,  # (row, col, tab)
                            rect,
                            self.view_frozen
                        )

                        cell_renderer.draw()

            # Undo scaling, translation, ...
            self.context.restore()

            self.context.show_page()


class GridCellCairoRenderer(object):
    """Renders a grid cell to a CairoSurface

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered
    * rect: 4 tuple of float
    \tx, y, width and height of cell rectangle

    """

    def __init__(self, context, code_array, key, rect, view_frozen=False):
        self.context = context
        self.code_array = code_array
        self.key = key
        self.rect = rect
        self.view_frozen = view_frozen

    def draw(self):
        """Draws cell to context"""

        cell_background_renderer = GridCellBackgroundCairoRenderer(
            self.context,
            self.code_array,
            self.key,
            self.rect,
            self.view_frozen)

        cell_content_renderer = GridCellContentCairoRenderer(
            self.context,
            self.code_array,
            self.key,
            self.rect)

        cell_border_renderer = GridCellBorderCairoRenderer(
            self.context,
            self.code_array,
            self.key,
            self.rect)

        cell_background_renderer.draw()
        cell_content_renderer.draw()
        cell_border_renderer.draw()


class GridCellContentCairoRenderer(object):
    """Renders cell content to Cairo context

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered

    """

    def __init__(self, context, code_array, key, rect):
        self.context = context
        self.code_array = code_array
        self.key = key
        self.rect = rect

    def get_cell_content(self):
        """Returns cell content"""

        try:
            if self.code_array.cell_attributes[self.key]["button_cell"]:
                return

        except IndexError:
            return

        try:
            return self.code_array[self.key]

        except IndexError:
            pass

    def _get_scalexy(self, ims_width, ims_height):
        """Returns scale_x, scale_y for bitmap display"""

        # Get cell attributes
        cell_attributes = self.code_array.cell_attributes[self.key]
        angle = cell_attributes["angle"]

        if abs(angle) == 90:
            scale_x = self.rect[3] / float(ims_width)
            scale_y = self.rect[2] / float(ims_height)

        else:
            # Normal case
            scale_x = self.rect[2] / float(ims_width)
            scale_y = self.rect[3] / float(ims_height)

        return scale_x, scale_y

    def _get_translation(self, ims_width, ims_height):
        """Returns x and y for a bitmap translation"""

        # Get cell attributes
        cell_attributes = self.code_array.cell_attributes[self.key]
        justification = cell_attributes["justification"]
        vertical_align = cell_attributes["vertical_align"]
        angle = cell_attributes["angle"]

        scale_x, scale_y = self._get_scalexy(ims_width, ims_height)
        scale = min(scale_x, scale_y)

        if angle not in (90, 180, -90):
            # Standard direction
            x = -2  # Otherwise there is a white border
            y = -2  # Otherwise there is a white border

            if scale_x > scale_y:
                if justification == "center":
                    x += (self.rect[2] - ims_width * scale) / 2

                elif justification == "right":
                    x += self.rect[2] - ims_width * scale

            else:
                if vertical_align == "middle":
                    y += (self.rect[3] - ims_height * scale) / 2

                elif vertical_align == "bottom":
                    y += self.rect[3] - ims_height * scale

        if angle == 90:
            x = -ims_width * scale + 2
            y = -2

            if scale_y > scale_x:
                if justification == "center":
                    y += (self.rect[2] - ims_height * scale) / 2

                elif justification == "right":
                    y += self.rect[2] - ims_height * scale

            else:
                if vertical_align == "middle":
                    x -= (self.rect[3] - ims_width * scale) / 2

                elif vertical_align == "bottom":
                    x -= self.rect[3] - ims_width * scale

        elif angle == 180:
            x = -ims_width * scale + 2
            y = -ims_height * scale + 2

            if scale_x > scale_y:
                if justification == "center":
                    x -= (self.rect[2] - ims_width * scale) / 2

                elif justification == "right":
                    x -= self.rect[2] - ims_width * scale

            else:
                if vertical_align == "middle":
                    y -= (self.rect[3] - ims_height * scale) / 2

                elif vertical_align == "bottom":
                    y -= self.rect[3] - ims_height * scale

        elif angle == -90:
            x = -2
            y = -ims_height * scale + 2

            if scale_y > scale_x:
                if justification == "center":
                    y -= (self.rect[2] - ims_height * scale) / 2

                elif justification == "right":
                    y -= self.rect[2] - ims_height * scale

            else:
                if vertical_align == "middle":
                    x += (self.rect[3] - ims_width * scale) / 2

                elif vertical_align == "bottom":
                    x += self.rect[3] - ims_width * scale

        return x, y

    def draw_bitmap(self, content):
        """Draws bitmap cell content to context"""

        if content.HasAlpha():
            image = wx.ImageFromBitmap(content)
            image.ConvertAlphaToMask()
            image.SetMask(False)
            content = wx.BitmapFromImage(image)

        ims = wx.lib.wxcairo.ImageSurfaceFromBitmap(content)

        ims_width = ims.get_width()
        ims_height = ims.get_height()

        transx, transy = self._get_translation(ims_width, ims_height)

        scale_x, scale_y = self._get_scalexy(ims_width, ims_height)
        scale = min(scale_x, scale_y)

        angle = float(self.code_array.cell_attributes[self.key]["angle"])

        self.context.save()
        self.context.rotate(-angle / 360 * 2 * math.pi)
        self.context.translate(transx, transy)
        self.context.scale(scale, scale)
        self.context.set_source_surface(ims, 0, 0)
        self.context.paint()
        self.context.restore()

    def draw_svg(self, svg_str):
        """Draws svg string to cell"""

        try:
            import rsvg
        except ImportError:
            self.draw_text(svg_str)
            return

        svg = rsvg.Handle(data=svg_str)

        svg_width, svg_height = svg.get_dimension_data()[:2]

        transx, transy = self._get_translation(svg_width, svg_height)

        scale_x, scale_y = self._get_scalexy(svg_width, svg_height)
        scale = min(scale_x, scale_y)

        angle = float(self.code_array.cell_attributes[self.key]["angle"])

        self.context.save()
        self.context.rotate(-angle / 360 * 2 * math.pi)
        self.context.translate(transx, transy)
        self.context.scale(scale, scale)
        svg.render_cairo(self.context)
        self.context.restore()

    def draw_matplotlib_figure(self, figure):
        """Draws matplotlib figure to context"""

        class CustomRendererCairo(RendererCairo):
            """Workaround for older versins with limited draw path length"""

            if sys.byteorder == 'little':
                BYTE_FORMAT = 0  # BGRA
            else:
                BYTE_FORMAT = 1  # ARGB

            def draw_path(self, gc, path, transform, rgbFace=None):
                ctx = gc.ctx
                transform = transform + Affine2D().scale(1.0, -1.0).\
                    translate(0, self.height)
                ctx.new_path()
                self.convert_path(ctx, path, transform)

                try:
                    self._fill_and_stroke(ctx, rgbFace, gc.get_alpha(),
                                          gc.get_forced_alpha())
                except AttributeError:
                    # Workaround for some Windiws version of Cairo
                    self._fill_and_stroke(ctx, rgbFace, gc.get_alpha())

            def draw_image(self, gc, x, y, im):
                # bbox - not currently used
                rows, cols, buf = im.color_conv(self.BYTE_FORMAT)
                surface = cairo.ImageSurface.create_for_data(
                    buf, cairo.FORMAT_ARGB32, cols, rows, cols*4)
                ctx = gc.ctx
                y = self.height - y - rows
                ctx.save()
                ctx.set_source_surface(surface, x, y)
                if gc.get_alpha() != 1.0:
                    ctx.paint_with_alpha(gc.get_alpha())
                else:
                    ctx.paint()
                ctx.restore()

        if pyplot is None:
            # Matplotlib is not installed
            return

        FigureCanvasCairo(figure)

        dpi = float(figure.dpi)

        # Set a border so that the figure is not cut off at the cell border
        border_x = 200 / (self.rect[2] / dpi) ** 2
        border_y = 200 / (self.rect[3] / dpi) ** 2

        width = (self.rect[2] - 2 * border_x) / dpi
        height = (self.rect[3] - 2 * border_y) / dpi

        figure.set_figwidth(width)
        figure.set_figheight(height)

        renderer = CustomRendererCairo(dpi)
        renderer.set_width_height(width, height)

        renderer.gc.ctx = self.context
        renderer.text_ctx = self.context

        self.context.save()
        self.context.translate(border_x, border_y + height * dpi)

        figure.draw(renderer)

        self.context.restore()

    def _get_text_color(self):
        """Returns text color rgb tuple of right line"""

        color = self.code_array.cell_attributes[self.key]["textcolor"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def set_font(self, pango_layout):
        """Sets the font for draw_text"""

        wx2pango_weights = {
            wx.FONTWEIGHT_BOLD: pango.WEIGHT_BOLD,
            wx.FONTWEIGHT_LIGHT: pango.WEIGHT_LIGHT,
            wx.FONTWEIGHT_NORMAL: pango.WEIGHT_NORMAL,
        }

        wx2pango_styles = {
            wx.FONTSTYLE_NORMAL: pango.STYLE_NORMAL,
            wx.FONTSTYLE_SLANT: pango.STYLE_OBLIQUE,
            wx.FONTSTYLE_ITALIC: pango.STYLE_ITALIC,
        }

        cell_attributes = self.code_array.cell_attributes[self.key]

        # Text font attributes
        textfont = cell_attributes["textfont"]
        pointsize = cell_attributes["pointsize"]
        fontweight = cell_attributes["fontweight"]
        fontstyle = cell_attributes["fontstyle"]
        underline = cell_attributes["underline"]
        strikethrough = cell_attributes["strikethrough"]

        # Now construct the pango font
        font_description = pango.FontDescription(
            " ".join([textfont, str(pointsize)]))
        pango_layout.set_font_description(font_description)

        attrs = pango.AttrList()

        # Underline
        attrs.insert(pango.AttrUnderline(underline, 0, MAX_RESULT_LENGTH))

        # Weight
        weight = wx2pango_weights[fontweight]
        attrs.insert(pango.AttrWeight(weight, 0, MAX_RESULT_LENGTH))

        # Style
        style = wx2pango_styles[fontstyle]
        attrs.insert(pango.AttrStyle(style, 0, MAX_RESULT_LENGTH))

        # Strikethrough
        attrs.insert(pango.AttrStrikethrough(strikethrough, 0,
                                             MAX_RESULT_LENGTH))

        pango_layout.set_attributes(attrs)

    def _rotate_cell(self, angle, rect, back=False):
        """Rotates and translates cell if angle in [90, -90, 180]"""

        if angle == 90 and not back:
            self.context.rotate(-math.pi / 2.0)
            self.context.translate(-rect[2] + 4, 0)

        elif angle == 90 and back:
            self.context.translate(rect[2] - 4, 0)
            self.context.rotate(math.pi / 2.0)

        elif angle == -90 and not back:
            self.context.rotate(math.pi / 2.0)
            self.context.translate(0, -rect[3] + 2)

        elif angle == -90 and back:
            self.context.translate(0, rect[3] - 2)
            self.context.rotate(-math.pi / 2.0)

        elif angle == 180 and not back:
            self.context.rotate(math.pi)
            self.context.translate(-rect[2] + 4, -rect[3] + 2)

        elif angle == 180 and back:
            self.context.translate(rect[2] - 4, rect[3] - 2)
            self.context.rotate(-math.pi)

    def draw_text(self, content):
        """Draws text cell content to context"""

        wx2pango_alignment = {
            "left": pango.ALIGN_LEFT,
            "center": pango.ALIGN_CENTER,
            "right": pango.ALIGN_RIGHT,
        }

        cell_attributes = self.code_array.cell_attributes[self.key]

        angle = cell_attributes["angle"]

        if angle in [-90, 90]:
            rect = self.rect[1], self.rect[0], self.rect[3], self.rect[2]
        else:
            rect = self.rect

        # Text color attributes
        self.context.set_source_rgb(*self._get_text_color())

        ptx = pangocairo.CairoContext(self.context)
        pango_layout = ptx.create_layout()
        self.set_font(pango_layout)

        pango_layout.set_wrap(pango.WRAP_WORD_CHAR)

        pango_layout.set_width(int(round((rect[2] - 4.0) * pango.SCALE)))

        try:
            markup = cell_attributes["markup"]
        except KeyError:
            # Old file
            markup = False

        if markup:
            with warnings.catch_warnings(record=True) as warning_lines:
                warnings.resetwarnings()
                warnings.simplefilter("always")
                pango_layout.set_markup(str(content))

                if warning_lines:
                    w2unicode = lambda m: str(m.message)
                    msg = "\n".join(map(w2unicode, warning_lines))
                    pango_layout.set_text(msg)
        else:
            pango_layout.set_text(str(content))

        alignment = cell_attributes["justification"]
        pango_layout.set_alignment(wx2pango_alignment[alignment])

        # Shift text for vertical alignment
        extents = pango_layout.get_pixel_extents()

        downshift = 0

        if cell_attributes["vertical_align"] == "bottom":
            downshift = rect[3] - extents[1][3] - 4

        elif cell_attributes["vertical_align"] == "middle":
            downshift = int((rect[3] - extents[1][3]) / 2) - 2

        self.context.save()

        self._rotate_cell(angle, rect)
        self.context.translate(0, downshift)

        ptx.update_layout(pango_layout)
        ptx.show_layout(pango_layout)

        self.context.restore()

    def draw_roundedrect(self, x, y, w, h, r=10):
        """Draws a rounded rectangle"""
        # A****BQ
        # H     C
        # *     *
        # G     D
        # F****E

        context = self.context

        context.save

        context.move_to(x+r, y)  # Move to A
        context.line_to(x+w-r, y)  # Straight line to B
        context.curve_to(x+w, y, x+w, y, x+w, y+r)  # Curve to C
        # Control points are both at Q
        context.line_to(x+w, y+h-r)  # Move to D
        context.curve_to(x+w, y+h, x+w, y+h, x+w-r, y+h)  # Curve to E
        context.line_to(x+r, y+h)  # Line to F
        context.curve_to(x, y+h, x, y+h, x, y+h-r)  # Curve to G
        context.line_to(x, y+r)  # Line to H
        context.curve_to(x, y, x, y, x+r, y)  # Curve to A

        context.restore

    def draw_button(self, x, y, w, h, label):
        """Draws a button"""

        context = self.context

        self.draw_roundedrect(x, y, w, h)
        context.clip()

        # Set up the gradients
        gradient = cairo.LinearGradient(0, 0, 0, 1)
        gradient.add_color_stop_rgba(0, 0.5, 0.5, 0.5, 0.1)
        gradient.add_color_stop_rgba(1, 0.8, 0.8, 0.8, 0.9)
#        # Transform the coordinates so the width and height are both 1
#        # We save the current settings and restore them afterward
        context.save()
        context.scale(w, h)
        context.rectangle(0, 0, 1, 1)
        context.set_source_rgb(0, 0, 1)
        context.set_source(gradient)
        context.fill()
        context.restore()

        # Draw the button text
        # Center the text
        x_bearing, y_bearing, width, height, x_advance, y_advance = \
            context.text_extents(label)

        text_x = (w / 2.0)-(width / 2.0 + x_bearing)
        text_y = (h / 2.0)-(height / 2.0 + y_bearing) + 1

        # Draw the button text
        context.move_to(text_x, text_y)
        context.set_source_rgba(0, 0, 0, 1)
        context.show_text(label)

        # Draw the border of the button
        context.move_to(x, y)
        context.set_source_rgba(0, 0, 0, 1)
        self.draw_roundedrect(x, y, w, h)
        context.stroke()

    def draw(self):
        """Draws cell content to context"""

        # Content is only rendered within rect
        self.context.save()
        self.context.rectangle(*self.rect)
        self.context.clip()

        content = self.get_cell_content()

        pos_x, pos_y = self.rect[:2]
        self.context.translate(pos_x + 2, pos_y + 2)

        cell_attributes = self.code_array.cell_attributes

        # Do not draw cell content if cell is too small
        # This allows blending out small cells by reducing height to 0

        if self.rect[2] < cell_attributes[self.key]["borderwidth_right"] or \
           self.rect[3] < cell_attributes[self.key]["borderwidth_bottom"]:
            self.context.restore()
            return

        if self.code_array.cell_attributes[self.key]["button_cell"]:
            # Render a button instead of the cell
            label = self.code_array.cell_attributes[self.key]["button_cell"]
            self.draw_button(1, 1, self.rect[2]-5, self.rect[3]-5, label)

        elif isinstance(content, wx._gdi.Bitmap):
            # A bitmap is returned --> Draw it!
            self.draw_bitmap(content)

        elif pyplot is not None and isinstance(content, pyplot.Figure):
            # A matplotlib figure is returned --> Draw it!
            self.draw_matplotlib_figure(content)

        elif isinstance(content, str) and is_svg(content):
            # The content is a vaid SVG xml string
            self.draw_svg(content)

        elif content is not None:
            self.draw_text(content)

        self.context.translate(-pos_x - 2, -pos_y - 2)

        # Remove clipping to rect
        self.context.restore()


class GridCellBackgroundCairoRenderer(object):
    """Renders cell background to Cairo context

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered
    * view_frozen: Bool
    \tIf true then paint frozen background pattern for frozen cells

    """

    def __init__(self, context, code_array, key, rect, view_frozen):
        self.context = context
        self.cell_attributes = code_array.cell_attributes
        self.key = key
        self.rect = rect
        self.view_frozen = view_frozen

    def _get_background_color(self):
        """Returns background color rgb tuple of right line"""

        color = self.cell_attributes[self.key]["bgcolor"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _draw_frozen_pattern(self):
        """Draws frozen pattern, i.e. diagonal lines"""

        self.context.save()

        x, y, w, h = self.rect
        self.context.set_source_rgb(0, 0, 1)
        self.context.set_line_width(0.25)
        self.context.rectangle(*self.rect)
        self.context.clip()

        for __x in numpy.arange(x-h, x+w, 5):
            self.context.move_to(__x, y + h)
            self.context.line_to(__x + h, y)
        self.context.stroke()

        self.context.restore()

    def draw(self):
        """Draws cell background to context"""

        self.context.set_source_rgb(*self._get_background_color())
        self.context.rectangle(*self.rect)
        self.context.fill()

        # If show frozen is active, show frozen pattern
        if self.view_frozen and self.cell_attributes[self.key]["frozen"]:
            self._draw_frozen_pattern()


class CellBorder(object):
    """Cell border

    Parameters
    ----------
    start_point: 2 tuple of Integer
    \tStart point of line
    end_point
    \tEnd point of line
    width: Float
    \tWidth of line
    color: 3-tuple of float
    \tRGB line color, each value is in [0, 1]

    """

    def __init__(self, start_point, end_point, width, color):
        self.start_point = start_point
        self.end_point = end_point
        self.width = width
        self.color = color

    def draw(self, context):
        """Draws self to Cairo context"""

        context.set_line_width(self.width)
        context.set_source_rgb(*self.color)

        context.move_to(*self.start_point)
        context.line_to(*self.end_point)
        context.stroke()


class Cell(object):
    """Cell"""

    def __init__(self, key, rect, cell_attributes):
        self.row, self.col, self.tab = self.key = key
        self.x, self.y, self.width, self.height = rect
        self.cell_attributes = cell_attributes

    def get_above_key_rect(self):
        """Returns tuple key rect of above cell"""

        key_above = self.row - 1, self.col, self.tab

        border_width_bottom = \
            float(self.cell_attributes[key_above]["borderwidth_bottom"]) / 2.0

        rect_above = (self.x, self.y-border_width_bottom,
                      self.width, border_width_bottom)
        return key_above, rect_above

    def get_below_key_rect(self):
        """Returns tuple key rect of below cell"""

        key_below = self.row + 1, self.col, self.tab

        border_width_bottom = \
            float(self.cell_attributes[self.key]["borderwidth_bottom"]) / 2.0

        rect_below = (self.x, self.y+self.height,
                      self.width, border_width_bottom)
        return key_below, rect_below

    def get_left_key_rect(self):
        """Returns tuple key rect of left cell"""

        key_left = self.row, self.col - 1, self.tab

        border_width_right = \
            float(self.cell_attributes[key_left]["borderwidth_right"]) / 2.0

        rect_left = (self.x-border_width_right, self.y,
                     border_width_right, self.height)
        return key_left, rect_left

    def get_right_key_rect(self):
        """Returns tuple key rect of right cell"""

        key_right = self.row, self.col + 1, self.tab

        border_width_right = \
            float(self.cell_attributes[self.key]["borderwidth_right"]) / 2.0

        rect_right = (self.x+self.width, self.y,
                      border_width_right, self.height)
        return key_right, rect_right

    def get_above_left_key_rect(self):
        """Returns tuple key rect of above left cell"""

        key_above_left = self.row - 1, self.col - 1, self.tab

        border_width_right = \
            float(self.cell_attributes[key_above_left]["borderwidth_right"]) \
            / 2.0
        border_width_bottom = \
            float(self.cell_attributes[key_above_left]["borderwidth_bottom"]) \
            / 2.0

        rect_above_left = (self.x-border_width_right,
                           self.y-border_width_bottom,
                           border_width_right, border_width_bottom)
        return key_above_left, rect_above_left

    def get_above_right_key_rect(self):
        """Returns tuple key rect of above right cell"""

        key_above = self.row - 1, self.col, self.tab
        key_above_right = self.row - 1, self.col + 1, self.tab

        border_width_right = \
            float(self.cell_attributes[key_above]["borderwidth_right"]) / 2.0
        border_width_bottom = \
            float(self.cell_attributes[key_above_right]["borderwidth_bottom"])\
            / 2.0

        rect_above_right = (self.x+self.width, self.y-border_width_bottom,
                            border_width_right, border_width_bottom)
        return key_above_right, rect_above_right

    def get_below_left_key_rect(self):
        """Returns tuple key rect of below left cell"""

        key_left = self.row, self.col - 1, self.tab
        key_below_left = self.row + 1, self.col - 1, self.tab

        border_width_right = \
            float(self.cell_attributes[key_below_left]["borderwidth_right"]) \
            / 2.0
        border_width_bottom = \
            float(self.cell_attributes[key_left]["borderwidth_bottom"]) / 2.0

        rect_below_left = (self.x-border_width_right, self.y-self.height,
                           border_width_right, border_width_bottom)
        return key_below_left, rect_below_left

    def get_below_right_key_rect(self):
        """Returns tuple key rect of below right cell"""

        key_below_right = self.row + 1, self.col + 1, self.tab

        border_width_right = \
            float(self.cell_attributes[self.key]["borderwidth_right"]) / 2.0
        border_width_bottom = \
            float(self.cell_attributes[self.key]["borderwidth_bottom"]) / 2.0

        rect_below_right = (self.x+self.width, self.y-self.height,
                            border_width_right, border_width_bottom)
        return key_below_right, rect_below_right


class CellBorders(object):
    """All 12 relevant borders around a cell

       tl   tr
        | t |
    lt -|---|- rt
        |l r|
    lb -|---|- rb
        | b |
       bl   br

    Parameters
    ----------
    key: 3 tuple
    \tCell key

    """

    def __init__(self, cell_attributes, key, rect):
        self.key = key
        self.rect = rect
        self.cell_attributes = cell_attributes
        self.cell = Cell(key, rect, cell_attributes)

    def _get_bottom_line_coordinates(self):
        """Returns start and stop coordinates of bottom line"""

        rect_x, rect_y, rect_width, rect_height = self.rect

        start_point = rect_x, rect_y + rect_height
        end_point = rect_x + rect_width, rect_y + rect_height

        return start_point, end_point

    def _get_right_line_coordinates(self):
        """Returns start and stop coordinates of right line"""

        rect_x, rect_y, rect_width, rect_height = self.rect

        start_point = rect_x + rect_width, rect_y
        end_point = rect_x + rect_width, rect_y + rect_height

        return start_point, end_point

    def _get_bottom_line_color(self):
        """Returns color rgb tuple of bottom line"""

        color = self.cell_attributes[self.key]["bordercolor_bottom"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_right_line_color(self):
        """Returns color rgb tuple of right line"""

        color = self.cell_attributes[self.key]["bordercolor_right"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_bottom_line_width(self):
        """Returns width of bottom line"""

        return float(self.cell_attributes[self.key]["borderwidth_bottom"]) / 2.

    def _get_right_line_width(self):
        """Returns width of right line"""

        return float(self.cell_attributes[self.key]["borderwidth_right"]) / 2.0

    def get_b(self):
        """Returns the bottom border of the cell"""

        start_point, end_point = self._get_bottom_line_coordinates()
        width = self._get_bottom_line_width()
        color = self._get_bottom_line_color()

        return CellBorder(start_point, end_point, width, color)

    def get_r(self):
        """Returns the right border of the cell"""

        start_point, end_point = self._get_right_line_coordinates()
        width = self._get_right_line_width()
        color = self._get_right_line_color()

        return CellBorder(start_point, end_point, width, color)

    def get_t(self):
        """Returns the top border of the cell"""

        cell_above = CellBorders(self.cell_attributes,
                                 *self.cell.get_above_key_rect())
        return cell_above.get_b()

    def get_l(self):
        """Returns the left border of the cell"""

        cell_left = CellBorders(self.cell_attributes,
                                *self.cell.get_left_key_rect())
        return cell_left.get_r()

    def get_tl(self):
        """Returns the top left border of the cell"""

        cell_above_left = CellBorders(self.cell_attributes,
                                      *self.cell.get_above_left_key_rect())
        return cell_above_left.get_r()

    def get_tr(self):
        """Returns the top right border of the cell"""

        cell_above = CellBorders(self.cell_attributes,
                                 *self.cell.get_above_key_rect())
        return cell_above.get_r()

    def get_rt(self):
        """Returns the right top border of the cell"""

        cell_above_right = CellBorders(self.cell_attributes,
                                       *self.cell.get_above_right_key_rect())
        return cell_above_right.get_b()

    def get_rb(self):
        """Returns the right bottom border of the cell"""

        cell_right = CellBorders(self.cell_attributes,
                                 *self.cell.get_right_key_rect())
        return cell_right.get_b()

    def get_br(self):
        """Returns the bottom right border of the cell"""

        cell_below = CellBorders(self.cell_attributes,
                                 *self.cell.get_below_key_rect())
        return cell_below.get_r()

    def get_bl(self):
        """Returns the bottom left border of the cell"""

        cell_below_left = CellBorders(self.cell_attributes,
                                      *self.cell.get_below_left_key_rect())
        return cell_below_left.get_r()

    def get_lb(self):
        """Returns the left bottom border of the cell"""

        cell_left = CellBorders(self.cell_attributes,
                                *self.cell.get_left_key_rect())
        return cell_left.get_b()

    def get_lt(self):
        """Returns the left top border of the cell"""

        cell_above_left = CellBorders(self.cell_attributes,
                                      *self.cell.get_above_left_key_rect())
        return cell_above_left.get_b()

    def gen_all(self):
        """Generator of all borders"""

        borderfuncs = [
            self.get_b, self.get_r, self.get_t, self.get_l,
            self.get_tl, self.get_tr, self.get_rt, self.get_rb,
            self.get_br, self.get_bl, self.get_lb, self.get_lt,
        ]

        for borderfunc in borderfuncs:
            yield borderfunc()


class GridCellBorderCairoRenderer(object):
    """Renders cell border to Cairo context

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3-tuple of Integer
    \tKey of cell to be rendered

    """

    def __init__(self, context, code_array, key, rect):
        self.context = context
        self.code_array = code_array
        self.cell_attributes = code_array.cell_attributes
        self.key = key
        self.rect = rect

    def draw(self):
        """Draws cell border to context"""

        # Lines should have a square cap to avoid ugly edges
        self.context.set_line_cap(cairo.LINE_CAP_SQUARE)

        self.context.save()
        self.context.rectangle(*self.rect)
        self.context.clip()

        cell_borders = CellBorders(self.cell_attributes, self.key, self.rect)
        borders = list(cell_borders.gen_all())
        borders.sort(key=attrgetter('width', 'color'))
        for border in borders:
            border.draw(self.context)

        self.context.restore()

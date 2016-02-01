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

pys
===

This file contains interfaces to the native pys file format.

It is split into the following sections

 * shape
 * code
 * attributes
 * row_heights
 * col_widths
 * macros

"""

import ast
from collections import OrderedDict
import src.lib.i18n as i18n


from src.lib.selection import Selection

from gettext import gettext as _


class Pys(object):
    """Interface between code_array and pys file

    The pys file is read from disk with the read method.
    The pys file is written to disk with the write method.

    Parameters
    ----------

    code_array: model.CodeArray object
    \tThe code_array object data structure
    pys_file: file
    \tFile like object in pys format

    """

    def __init__(self, code_array, pys_file):
        self.code_array = code_array
        self.pys_file = pys_file

        self._section2reader = {
            "[Pyspread save file version]\n": self._pys_assert_version,
            "[shape]\n": self._pys2shape,
            "[grid]\n": self._pys2code,
            "[attributes]\n": self._pys2attributes,
            "[row_heights]\n": self._pys2row_heights,
            "[col_widths]\n": self._pys2col_widths,
            "[macros]\n": self._pys2macros,
        }

        self._section2writer = OrderedDict([
            ("[Pyspread save file version]\n", self._version2pys),
            ("[shape]\n", self._shape2pys),
            ("[grid]\n", self._code2pys),
            ("[attributes]\n", self._attributes2pys),
            ("[row_heights]\n", self._row_heights2pys),
            ("[col_widths]\n", self._col_widths2pys),
            ("[macros]\n", self._macros2pys),
        ])

    def _split_tidy(self, string, maxsplit=None):
        """Rstrips string for \n and splits string for \t"""

        if maxsplit is None:
            return string.rstrip("\n").split("\t")
        else:
            return string.rstrip("\n").split("\t", maxsplit)

    def _get_key(self, *keystrings):
        """Returns int key tuple from key string list"""

        return tuple(map(int, keystrings))

    def _pys_assert_version(self, line):
        """Asserts pys file version"""

        if float(line.strip()) > 1.0:
            # Abort if file version not supported
            msg = _("File version {version} unsupported (>1.0).").format(
                version=line.strip())
            raise ValueError(msg)

    def _version2pys(self):
        """Writes pys file version to pys file

        Format: <version>\n

        """

        self.pys_file.write("0.1\n")

    def _shape2pys(self):
        """Writes shape to pys file

        Format: <rows>\t<cols>\t<tabs>\n

        """

        shape_line = "\t".join(map(str, self.code_array.shape)) + "\n"
        self.pys_file.write(shape_line)

    def _pys2shape(self, line):
        """Updates shape in code_array"""

        self.code_array.shape = self._get_key(*self._split_tidy(line))

    def _code2pys(self):
        """Writes code to pys file

        Format: <row>\t<col>\t<tab>\t<code>\n

        """

        for key in self.code_array:
            key_str = "\t".join(repr(ele) for ele in key)
            code_str = self.code_array(key)
            out_str = key_str + "\t" + code_str + "\n"

            self.pys_file.write(out_str.encode("utf-8"))

    def _pys2code(self, line):
        """Updates code in pys code_array"""

        row, col, tab, code = self._split_tidy(line, maxsplit=3)
        key = self._get_key(row, col, tab)

        self.code_array.dict_grid[key] = str(code, encoding='utf-8')

    def _attributes2pys(self):
        """Writes attributes to pys file

        Format:
        <selection[0]>\t[...]\t<tab>\t<key>\t<value>\t[...]\n

        """

        # Remove doublettes
        purged_cell_attributes = []
        purged_cell_attributes_keys = []
        for selection, tab, attr_dict in self.code_array.cell_attributes:
            if purged_cell_attributes_keys and \
               (selection, tab) == purged_cell_attributes_keys[-1]:
                purged_cell_attributes[-1][2].update(attr_dict)
            else:
                purged_cell_attributes_keys.append((selection, tab))
                purged_cell_attributes.append([selection, tab, attr_dict])

        for selection, tab, attr_dict in purged_cell_attributes:
            sel_list = [selection.block_tl, selection.block_br,
                        selection.rows, selection.cols, selection.cells]

            tab_list = [tab]

            attr_dict_list = []
            for key in attr_dict:
                attr_dict_list.append(key)
                attr_dict_list.append(attr_dict[key])

            line_list = list(map(repr, sel_list + tab_list + attr_dict_list))

            self.pys_file.write("\t".join(line_list) + "\n")

    def _pys2attributes(self, line):
        """Updates attributes in code_array"""

        splitline = self._split_tidy(line)

        selection_data = list(map(ast.literal_eval, splitline[:5]))
        selection = Selection(*selection_data)

        tab = int(splitline[5])

        attrs = {}
        for col, ele in enumerate(splitline[6:]):
            if not (col % 2):
                # Odd entries are keys
                key = ast.literal_eval(ele)

            else:
                # Even cols are values
                attrs[key] = ast.literal_eval(ele)

        self.code_array.cell_attributes.append((selection, tab, attrs))

    def _row_heights2pys(self):
        """Writes row_heights to pys file

        Format: <row>\t<tab>\t<value>\n

        """

        for row, tab in self.code_array.dict_grid.row_heights:
            if row < self.code_array.shape[0] and \
               tab < self.code_array.shape[2]:
                height = self.code_array.dict_grid.row_heights[(row, tab)]
                height_strings = list(map(repr, [row, tab, height]))
                self.pys_file.write("\t".join(height_strings) + "\n")

    def _pys2row_heights(self, line):
        """Updates row_heights in code_array"""

        # Split with maxsplit 3
        split_line = self._split_tidy(line)
        key = row, tab = self._get_key(*split_line[:2])
        height = float(split_line[2])

        shape = self.code_array.shape

        try:
            if row < shape[0] and tab < shape[2]:
                self.code_array.row_heights[key] = height

        except ValueError:
            pass

    def _col_widths2pys(self):
        """Writes col_widths to pys file

        Format: <col>\t<tab>\t<value>\n

        """

        for col, tab in self.code_array.dict_grid.col_widths:
            if col < self.code_array.shape[1] and \
               tab < self.code_array.shape[2]:
                width = self.code_array.dict_grid.col_widths[(col, tab)]
                width_strings = list(map(repr, [col, tab, width]))
                self.pys_file.write("\t".join(width_strings) + "\n")

    def _pys2col_widths(self, line):
        """Updates col_widths in code_array"""

        # Split with maxsplit 3
        split_line = self._split_tidy(line)
        key = col, tab = self._get_key(*split_line[:2])
        width = float(split_line[2])

        shape = self.code_array.shape

        try:
            if col < shape[1] and tab < shape[2]:
                self.code_array.col_widths[key] = width

        except ValueError:
            pass

    def _macros2pys(self):
        """Writes macros to pys file

        Format: <macro code line>\n

        """

        macros = self.code_array.dict_grid.macros
        pys_macros = macros.encode("utf-8")
        self.pys_file.write(pys_macros)

    def _pys2macros(self, line):
        """Updates macros in code_array"""

        if self.code_array.dict_grid.macros and \
           self.code_array.dict_grid.macros[-1] != "\n":
            # The last macro line does not end with \n
            # Therefore, if not new line is inserted, the codeis broken
            self.code_array.dict_grid.macros += "\n"

        self.code_array.dict_grid.macros += line.decode("utf-8")

    # Access via model.py data
    # ------------------------

    def from_code_array(self):
        """Replaces everything in pys_file from code_array"""

        for key in self._section2writer:
            self.pys_file.write(key)
            self._section2writer[key]()

            try:
                if self.pys_file.aborted:
                    break
            except AttributeError:
                # pys_fileis not opened via fileio.BZAopen
                pass

    def to_code_array(self):
        """Replaces everything in code_array from pys_file"""

        state = None

        # Check if version section starts with first line
        first_line = True

        # Reset pys_file to start to enable multiple calls of this method
        self.pys_file.seek(0)

        for line in self.pys_file:
            if first_line:
                # If Version section does not start with first line then
                # the file is invalid.
                if line == "[Pyspread save file version]\n":
                    first_line = False
                else:
                    raise ValueError(_("File format unsupported."))

            if line in self._section2reader:
                state = line

            elif state is not None:
                self._section2reader[state](line)

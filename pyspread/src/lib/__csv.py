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
csvlib
======

Provides
--------

 * sniff: Sniffs CSV dialect and header info
 * get_first_line
 * csv_digest_gen
 * cell_key_val_gen
 * Digest: Converts any object to target type as good as possible
 * CsvInterface
 * TxtGenerator

"""

import ast
import csv
import datetime
import os
import types

import wx

from src.config import config

from src.gui._events import post_command_event, StatusBarEventMixin

from src.lib.fileio import AOpen

from gettext import gettext as _


def sniff(filepath):
    """
    Sniffs CSV dialect and header info from csvfilepath

    Returns a tuple of dialect and has_header

    """

    with open(filepath, "rb") as csvfile:
        sample = csvfile.read(config["sniff_size"])

    sniffer = csv.Sniffer()
    dialect = sniffer.sniff(sample)()
    has_header = sniffer.has_header(sample)

    return dialect, has_header


def get_first_line(filepath, dialect):
    """Returns List of first line items of file filepath"""

    with open(filepath, "rb") as csvfile:
        csvreader = csv.reader(csvfile, dialect=dialect)

        for first_line in csvreader:
            break

    return first_line


def digested_line(line, digest_types):
    """Returns list of digested values in line"""

    digested_line = []
    for i, ele in enumerate(line):
        try:
            digest_key = digest_types[i]

        except IndexError:
            digest_key = digest_types[0]

        digest = Digest(acceptable_types=[digest_key])

        try:
            digested_line.append(repr(digest(ele)))

        except Exception:
            digested_line.append("")

    return digested_line


def csv_digest_gen(filepath, dialect, has_header, digest_types):
    """Generator of digested values from csv file in filepath

    Parameters
    ----------
    filepath:String
    \tFile path of csv file to read
    dialect: Object
    \tCsv dialect
    digest_types: tuple of types
    \tTypes of data for each col

    """

    with open(filepath, "rb") as csvfile:
        csvreader = csv.reader(csvfile, dialect=dialect)

        if has_header:
            # Ignore first line
            for line in csvreader:
                break

        for line in csvreader:
            yield digested_line(line, digest_types)


def cell_key_val_gen(iterable, shape, topleft=(0, 0)):
    """Generator of row, col, value tuple from iterable of iterables

    it: Iterable of iterables
    \tMatrix that shall be mapped on target grid
    shape: Tuple of Integer
    \tShape of target grid
    topleft: 2-tuple of Integer
    \tTop left cell for insertion of it

    """

    top, left = topleft

    for __row, line in enumerate(iterable):
        row = top + __row
        if row >= shape[0]:
            break

        for __col, value in enumerate(line):
            col = left + __col
            if col >= shape[1]:
                break

            yield row, col, value


def encode_gen(line, encoding="utf-8"):
    """Encodes all Unicode strings in line to encoding

    Parameters
    ----------
    line: Iterable of Unicode strings
    \tDate to be encoded
    encoding: String, defaults to "utf-8"
    \tTarget encoding

    """

    for ele in line:
        if isinstance(ele, str):
            yield ele.encode(encoding)
        else:
            yield ele


class Digest(object):
    """
    Maps types to types that are acceptable for target class

    The Digest class handles data of unknown type. Its objects are
    callable. They return an acceptable data type, which may be the fallback
    data type if everything else fails.

    The Digest class is intended to be subclassed by the target class.

    Parameters:
    -----------

    acceptable_types: list of types, defaults to None
    \tTypes that are acceptable for the target_class.
    \tThey are ordered highest preference first
    \tIf None, the string representation of the object is returned

    fallback_type: type, defaults to types.UnicodeType
    \t

    """

    def __init__(self, acceptable_types=None, fallback_type=None,
                 encoding="utf-8"):

        if acceptable_types is None:
            acceptable_types = [None]

        self.acceptable_types = acceptable_types
        self.fallback_type = fallback_type
        self.encoding = encoding

        # Type conversion functions

        def make_string(obj):
            """Makes a string object from any object"""

            if type(obj) is bytes:
                return obj

            if obj is None:
                return ""
            try:
                return str(obj)

            except Exception:
                return repr(obj)

        def make_unicode(obj):
            """Makes a unicode object from any object"""

            if type(obj) is str:
                return obj

            elif isinstance(obj, bytes):
                # Try UTF-8
                return obj.decode(self.encoding)

            if obj is None:
                return ""

            try:
                return str(obj)

            except Exception:
                return repr(obj)

        def make_slice(obj):
            """Makes a slice object from slice or int"""

            if isinstance(obj, slice):
                return obj

            try:
                return slice(obj, obj + 1, None)

            except Exception:
                return None

        def make_date(obj):
            """Makes a date from comparable types"""

            from dateutil.parser import parse

            try:
                return parse(obj).date()

            except Exception:
                return None

        def make_datetime(obj):
            """Makes a datetime from comparable types"""

            from dateutil.parser import parse

            try:
                return parse(obj)

            except Exception:
                return None

        def make_time(obj):
            """Makes a time from comparable types"""

            from dateutil.parser import parse

            try:
                return parse(obj).time()

            except Exception:
                return None

        def make_object(obj):
            """Returns the object"""
            try:
                return ast.literal_eval(obj)

            except Exception:
                return None

        self.typehandlers = {
            None: repr,
            bytes: make_string,
            str: make_unicode,
            slice: make_slice,
            bool: bool,
            object: make_object,
            int: int,
            float: float,
            types.CodeType: make_object,
            datetime.date: make_date,
            datetime.datetime: make_datetime,
            datetime.time: make_time,
        }

        if self.fallback_type is not None and \
           self.fallback_type not in self.typehandlers:

            err_msg = _("Fallback type {type} unknown.").\
                format(type=str(self.fallback_type))

            raise NotImplementedError(err_msg)

    def __call__(self, orig_obj):
        """Returns acceptable object"""

        errormessage = ""

        type_found = False

        for target_type in self.acceptable_types:
            if target_type in self.typehandlers:
                type_found = True
                break
        if not type_found:
            target_type = self.fallback_type

        try:
            acceptable_obj = self.typehandlers[target_type](orig_obj)
            return acceptable_obj
        except TypeError as err:
            errormessage += str(err)

        try:
            acceptable_obj = self.typehandlers[self.fallback_type](orig_obj)
            return acceptable_obj
        except TypeError as err:
            errormessage += str(err)

        return errormessage

# end of class Digest


class CsvInterface(StatusBarEventMixin):
    """CSV interface class

    Provides
    --------
     * __iter__: CSV reader - generator of generators of csv data cell content
     * write: CSV writer

    """

    def __init__(self, main_window, path, dialect, digest_types, has_header,
                 encoding='utf-8'):
        self.main_window = main_window
        self.path = path
        self.csvfilename = os.path.split(path)[1]

        self.dialect = dialect
        self.digest_types = digest_types
        self.has_header = has_header

        self.encoding = encoding

        self.first_line = False

    def __iter__(self):
        """Generator of generators that yield csv data"""

        with AOpen(self.path, "rb", main_window=self.main_window) as csv_file:
            csv_reader = csv.reader(csv_file, self.dialect)

            self.first_line = self.has_header

            for line in csv_reader:
                yield self._get_csv_cells_gen(line)
                break

            self.first_line = False

            for line in csv_reader:
                yield self._get_csv_cells_gen(line)

        msg = _("File {filename} imported successfully.").format(
            filename=self.csvfilename)
        post_command_event(self.main_window, self.StatusBarMsg, text=msg)

    def _get_csv_cells_gen(self, line):
        """Generator of values in a csv line"""

        digest_types = self.digest_types

        for j, value in enumerate(line):
            if self.first_line:
                digest_key = None
                digest = lambda x: x.decode(self.encoding)
            else:
                try:
                    digest_key = digest_types[j]
                except IndexError:
                    digest_key = digest_types[0]

                digest = Digest(acceptable_types=[digest_key],
                                encoding=self.encoding)

            try:
                digest_res = digest(value)

                if digest_res == "\b":
                    digest_res = None

                elif digest_key is not types.CodeType:
                    digest_res = repr(digest_res)

            except Exception:
                digest_res = ""

            yield digest_res

    def write(self, iterable):
        """Writes values from iterable into CSV file"""

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=self.path)

        try:

            with open(self.path, "wb") as csvfile:
                csv_writer = csv.writer(csvfile, self.dialect)

                for line in iterable:
                    csv_writer.writerow(
                        list(encode_gen(line, encoding=self.encoding)))

        except IOError:
            txt = \
                _("Error opening file {filepath}.").format(filepath=self.path)
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=txt)
            except TypeError:
                # The main window does not exist any more
                pass

            return False


class TxtGenerator(StatusBarEventMixin):
    """Generator of generators of Whitespace separated txt file cell content"""

    def __init__(self, main_window, path):
        self.main_window = main_window
        try:
            self.infile = open(path)

        except IOError:
            statustext = "Error opening file " + path + "."
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)
            self.infile = None

    def __iter__(self):

        # If self.infile is None then stopiteration is reached immediately
        if self.infile is None:
            return

        for line in self.infile:
            yield (col for col in line.split())

        self.infile.close()

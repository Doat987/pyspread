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

fileio
======

This module provides file reader and writer classes.
These classes behave like open but provide status messages and can be aborted.


Provides
--------

 * AOpen: Read and write files with status messages and abort option

"""

import bz2
import io
from . import i18n

import wx

from src.gui._events import post_command_event
from src.sysvars import is_gtk

from gettext import gettext as _


class AOpenMixin(object):
    """AOpen mixin class"""

    def set_initial_state(self, kwargs):
        """Sets class state from kwargs attributes, pops extra kwargs"""

        self.main_window = kwargs.pop("main_window")

        try:
            statustext = kwargs.pop("statustext")

        except KeyError:
            statustext = ""

        try:
            self.total_lines = kwargs.pop("total_lines")
            self.statustext = statustext + \
                _("{nele} of {totalele} elements processed.")

        except KeyError:
            self.total_lines = None
            self.statustext = statustext + _("{nele} elements processed.")

        try:
            self.freq = kwargs.pop("freq")

        except KeyError:
            self.freq = 1000

        # The aborted attribute makes next() to raise StopIteration
        self.aborted = False

        # Line counter
        self.line = 0

        # Bindings
        self.main_window.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def __next__(self):

        """Next that shows progress in statusbar for each <freq> cells"""

        self.progress_status()

        # Check abortes state and raise StopIteration if aborted
        if self.aborted:
            statustext = _("File loading aborted.")
            post_command_event(self.main_window, self.main_window.StatusBarMsg,
                               text=statustext)
            raise StopIteration

        return self.parent_cls.next(self)

    def write(self, *args, **kwargs):
        """Write that shows progress in statusbar for each <freq> cells"""

        self.progress_status()

        # Check abortes state and raise StopIteration if aborted
        if self.aborted:
            statustext = _("File saving aborted.")
            post_command_event(self.main_window, self.main_window.StatusBarMsg,
                               text=statustext)
            return False

        return self.parent_cls.write(self, *args, **kwargs)

    def progress_status(self):
        """Displays progress in statusbar"""

        if self.line % self.freq == 0:
            text = self.statustext.format(nele=self.line,
                                          totalele=self.total_lines)

            if self.main_window.grid.actions.pasting:
                try:
                    post_command_event(self.main_window,
                                       self.main_window.StatusBarMsg,
                                       text=text)
                except TypeError:
                    # The main window does not exist any more
                    pass
            else:
                # Write directly to the status bar because the event queue
                # is not emptied during file access

                self.main_window.GetStatusBar().SetStatusText(text)

            # Now wait for the statusbar update to be written on screen
            if is_gtk():
                try:
                    wx.Yield()
                except:
                    pass

        self.line += 1

    def on_key(self, event):
        """Sets aborted state if escape is pressed"""

        if self.main_window.grid.actions.pasting and \
           event.GetKeyCode() == wx.WXK_ESCAPE:
            self.aborted = True

        event.Skip()


class AOpen(AOpenMixin, io.TextIOBase):
    """Read and write files with status messages and abort option

    Extra Key Word Parameters (extends open)
    ----------------------------------------

    main_window: Object
    \tMain window object, must be set
    statustext: String, defaults to ""
    \tLeft text in statusbar to be displayed
    total_lines: Integer, defaults to None
    \tThe number of elements that have to be processed
    freq: Integer, defaults to 1000
    \tNo. operations between two abort possibilities

    """

    parent_cls = io.TextIOBase

    def __init__(self, *args, **kwargs):

        self.set_initial_state(kwargs)

        io.TextIOBase.__init__(self, *args, **kwargs)


class Bz2AOpen(AOpenMixin, bz2.BZ2File):
    """Read and write bz2 files with status messages and abort option

    Extra Key Word Parameters (extends open)
    ----------------------------------------

    main_window: Object
    \tMain window object, must be set
    statustext: String, defaults to ""
    \tLeft text in statusbar to be displayed
    total_lines: Integer, defaults to None
    \tThe number of elements that have to be processed
    freq: Integer, defaults to 1000
    \tNo. operations between two abort possibilities

    """

    parent_cls = bz2.BZ2File

    def __init__(self, *args, **kwargs):

        self.set_initial_state(kwargs)

        bz2.BZ2File.__init__(self, *args, **kwargs)

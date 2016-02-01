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

gpg
===

GPG handling functions

Provides
--------

 * genkey: Generates gpg key
 * sign: Returns detached signature for file
 * verify: verifies stream against signature

"""

import wx
import gnupg

import src.lib.i18n as i18n
from src.config import config
from src.gui._gui_interfaces import get_key_params_from_user
from gettext import gettext as _


def _eq_keyid(fingerprint1, fingerprint2):
    """Returns True if keyids for fingerprints match, False otherwise"""

    keyid = fingerprint2keyid(fingerprint1)
    pyspread_keyid = fingerprint2keyid(fingerprint2)
    return keyid == pyspread_keyid


def choose_key(gpg_private_keys):
    """Displays gpg key choice and returns key"""

    uid_strings_fp = []
    uid_string_fp2key = {}

    current_key_index = None

    for i, key in enumerate(gpg_private_keys):
        fingerprint = key['fingerprint']

        if _eq_keyid(fingerprint, config["gpg_key_fingerprint"]):
            current_key_index = i

        for uid_string in key['uids']:
            uid_string_fp = '"' + uid_string + ' (' + fingerprint + ')'
            uid_strings_fp.append(uid_string_fp)
            uid_string_fp2key[uid_string_fp] = key

    msg = _('Choose a GPG key for signing pyspread save files.\n'
            'The GPG key must not have a passphrase set.')

    dlg = wx.SingleChoiceDialog(None, msg, _('Choose key'), uid_strings_fp,
                                wx.CHOICEDLG_STYLE)

    childlist = list(dlg.GetChildren())
    childlist[-3].SetLabel(_("Use chosen key"))
    childlist[-2].SetLabel(_("Create new key"))

    if current_key_index is not None:
        # Set choice to current key
        dlg.SetSelection(current_key_index)

    if dlg.ShowModal() == wx.ID_OK:
        uid_string_fp = dlg.GetStringSelection()
        key = uid_string_fp2key[uid_string_fp]

    else:
        key = None

    dlg.Destroy()

    return key


def _register_key(fingerprint, gpg):
    """Registers key in config"""

    for private_key in gpg.list_keys(True):
        try:
            if str(fingerprint) == private_key['fingerprint']:
                config["gpg_key_fingerprint"] = \
                    repr(private_key['fingerprint'])
        except KeyError:
            pass


def genkey(key_name=None):
    """Creates a new standard GPG key

    Parameters
    ----------

    ui: Bool
    \tIf True, then a new key is created when required without user interaction

    """

    gpg_key_param_list = [
        ('key_type', 'DSA'),
        ('key_length', '2048'),
        ('subkey_type', 'ELG-E'),
        ('subkey_length', '2048'),
        ('expire_date', '0'),
    ]

    gpg = gnupg.GPG()

    gpg.encoding = 'utf-8'

    # Check if standard key is already present

    pyspread_key_fingerprint = config["gpg_key_fingerprint"]
    gpg_private_keys = gpg.list_keys(True)
    gpg_private_fingerprints = gpg.list_keys(True).fingerprints

    pyspread_key = None

    for private_key, fingerprint in zip(gpg_private_keys,
                                        gpg_private_fingerprints):
        if str(pyspread_key_fingerprint) == fingerprint:
            pyspread_key = private_key

    if key_name is None and pyspread_key is None:
        # If no GPG key is set in config, choose one
        pyspread_key = choose_key(gpg_private_keys)

    if pyspread_key:
        # A key has been chosen
        config["gpg_key_fingerprint"] = repr(pyspread_key['fingerprint'])

    else:
        # No key has been chosen --> Create new one
        if key_name is None:
            gpg_key_parameters = get_key_params_from_user(gpg_key_param_list)
            if gpg_key_parameters is None:
                # No name entered
                return
        else:
            gpg_key_param_list.append(
                ('name_real', '{key_name}'.format(key_name=key_name)))
            gpg_key_parameters = dict(gpg_key_param_list)

        input_data = gpg.gen_key_input(**gpg_key_parameters)

        # Generate key
        # ------------

        if key_name is None:
            # Show information dialog

            style = wx.ICON_INFORMATION | wx.DIALOG_NO_PARENT | wx.OK | \
                wx.CANCEL
            pyspread_key_uid = gpg_key_parameters["name_real"]
            short_message = _("New GPG key").format(pyspread_key_uid)
            message = _("After confirming this dialog, a new GPG key ") + \
                _("'{key}' will be generated.").format(key=pyspread_key_uid) +\
                _(" \n \nThis may take some time.\nPlease wait.")
            dlg = wx.MessageDialog(None, message, short_message, style)
            dlg.Centre()

            if dlg.ShowModal() == wx.ID_OK:
                dlg.Destroy()
                gpg_key = gpg.gen_key(input_data)
                _register_key(gpg_key, gpg)
                fingerprint = gpg_key.fingerprint
            else:
                dlg.Destroy()
                return

        else:
            gpg_key = gpg.gen_key(input_data)
            _register_key(gpg_key, gpg)
            fingerprint = gpg_key.fingerprint

    return fingerprint


def fingerprint2keyid(fingerprint):
    """Returns keyid from fingerprint for private keys"""

    gpg = gnupg.GPG()
    private_keys = gpg.list_keys(True)

    keyid = None
    for private_key in private_keys:
        if private_key['fingerprint'] == config["gpg_key_fingerprint"]:
            keyid = private_key['keyid']
            break

    return keyid


def sign(filename):
    """Returns detached signature for file"""

    gpg = gnupg.GPG()

    with open(filename, "rb") as signfile:
        keyid = fingerprint2keyid(config["gpg_key_fingerprint"])

        if keyid is None:
            msg = "No private key for fingerprint {}."
            raise ValueError(msg.format(config["gpg_key_fingerprint"]))

        signed_data = gpg.sign_file(signfile, keyid=keyid, detach=True)

    return signed_data


def verify(sigfilename, filefilename=None):
    """Verifies a signature, returns True if successful else False."""

    gpg = gnupg.GPG()

    with open(sigfilename, "rb") as sigfile:
        verified = gpg.verify_file(sigfile, filefilename)

        pyspread_keyid = fingerprint2keyid(config["gpg_key_fingerprint"])

        if verified.valid and verified.key_id == pyspread_keyid:
            return True

    return False

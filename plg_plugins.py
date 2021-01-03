## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «plugins» - MCP and MythTV Plugin enablement plugin
#
# Modifications copyright (C) 2020, Ted (MythTV forum member heyted)
# Original Copyright (C) 2009, Mario Limonciello, for Mythbuntu
#
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this application; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##################################################################################

from MythbuntuControlPanel.plugin import MCPPlugin
from gi.repository import Gtk
import os
import string
import logging
import configparser

from MythbuntuControlPanel.dictionaries import *

class MythPluginsPlugin(MCPPlugin):
    """A tool for enabling MythTV plugins"""

    CONFIGFILE = "/etc/default/mythweb"

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Plugins"
        information["icon"] = "gtk-add"
        information["ui"] = "tab_plugins"
        self.config = configparser.RawConfigParser()
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it into the plugin's own internal structures"""
        #Dictionaries
        self.dictionary_state={}
        for list in get_frontend_plugin_dictionary(self), \
                    get_backend_plugin_dictionary(self):
            for item in list:
                self.dictionary_state[list[item]]=self.query_installed(item)

        #Mythweb auth
        self.mythweb_auth={}
        found_cfg=False
        if os.path.exists(self.CONFIGFILE):
            self.config.read(self.CONFIGFILE)
            try:
                self.mythweb_auth['enable'] = self.config.getboolean("cfg", "enable")
                self.mythweb_auth['user'] = self.config.getboolean("cfg", "username")
                self.mythweb_auth['pass'] = self.config.getboolean("cfg", "password")
                found_cfg=True
            except Exception:
                pass
        if not found_cfg:
            self.mythweb_auth['enable'] = os.path.exists('/etc/mythtv/mythweb-digest')
            self.mythweb_auth['user'] = ""
            self.mythweb_auth['pass'] = ""

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""

        #Load the detected dictionary
        for item in self.dictionary_state:
            item.set_active(self.dictionary_state[item])

        #Mythweb auth
        self.password_table.hide()
        self.mythweb_username.set_text("")
        self.mythweb_password.set_text("")
        model = self.mythweb_password_combobox1.get_model()
        if len(model) > 2:
            iter = model.get_iter(Gtk.TreePath([2,0]))
            model.remove(iter)
        self.mythweb_password_combobox1.remove_all()
        self.mythweb_password_combobox1.append_text("Disable")
        self.mythweb_password_combobox1.append_text("Enable")
        if self.mythweb_auth['enable']:
            #self.mythweb_password_combobox1.set_active_iter(model.get_iter(Gtk.TreePath([0,1])))
            self.mythweb_password_combobox1.set_active(1)
            self.mythweb_password_combobox1.append_text("Reconfigure")
        else:
            self.mythweb_password_combobox1.set_active(0)
            #self.mythweb_password_combobox1.set_active_iter(model.get_iter(Gtk.TreePath([0,0])))

        self.toggle_plugins(self.mythweb_checkbox)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)

        #Installable items
        for list in get_frontend_plugin_dictionary(self), \
                    get_backend_plugin_dictionary(self):
            for item in list:
                if list[item].get_active() != self.dictionary_state[list[item]]:
                    if list[item].get_active():
                        self._markInstall(item)
                    else:
                        self._markRemove(item)

        #Mythweb auth
        if self.mythweb_password_combobox1.get_active() != self.mythweb_auth['enable']:
            self._markReconfigureRoot("mythweb_auth",self.mythweb_password_combobox1.get_active() > 0)
        if self.mythweb_password_combobox1.get_active():
            if self.mythweb_username.get_text() != self.mythweb_auth['user']:
                self._markReconfigureRoot("mythweb_user",self.mythweb_username.get_text())
            if self.mythweb_password.get_text() != self.mythweb_auth['pass']:
                self._markReconfigureRoot("mythweb_password",self.mythweb_password.get_text())

    def toggle_plugins(self,widget):
        if widget is not None:
            if widget.get_name() == "mythweb_checkbox":
                self.mythweb_password_combobox1.set_sensitive(widget.get_active())
                if not widget.get_active():
                    self.mythweb_password_combobox1.set_active(0)

            elif widget.get_name() == "mythweb_username" or \
                 widget.get_name() == "mythweb_password":
                username = self.mythweb_username.get_text().split(' ')[0]
                password = self.mythweb_password.get_text().split(' ')[0]
                if self.mythweb_password_combobox1.get_active() != 2 or \
                   (len(username) > 0 and len(password) > 0):
                    self._incomplete=False
                else:
                    self._incomplete=True

            elif widget.get_name() == "mythweb_password_combobox1":
                iteration=1
                if self.mythweb_auth['enable']:
                    iteration = 2
                if widget.get_active() == iteration:
                    self.password_table.show()
                    self._incomplete=True
                else:
                    self.mythweb_username.set_text("")
                    self.mythweb_password.set_text("")
                    self.password_table.hide()
                    self._incomplete=False

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""

        found_cfg = False
        print(self.CONFIGFILE)
        if os.path.exists(self.CONFIGFILE):
            try:
                self.config.read(self.CONFIGFILE)
                if not self.config.has_section('cfg'):
                  self.config.add_section("cfg")
                found_cfg = True
            except Exception:
                pass
        if not found_cfg:
            self.config.add_section("cfg")
            self.config.set("cfg", "enable", "false")
            self.config.set("cfg", "only", "false")
            self.config.set("cfg", "username", "")
            self.config.set("cfg", "password", "")

        for item in reconfigure:
            if item == "mythweb_auth":
                if not reconfigure[item]:
                    if os.path.exists('/etc/mythtv/mythweb-digest'):
                        os.remove('/etc/mythtv/mythweb-digest')
                    self.config.set("cfg", "enable", "false")
                else:
                    self.config.set("cfg", "enable", "true")
            elif item == "mythweb_user":
                self.config.set("cfg", "username", reconfigure[item])
            elif item == "mythweb_password":
                self.config.set("cfg", "password", reconfigure[item])

        with open(self.CONFIGFILE, 'w') as configfile:
            self.config.write(configfile)
        os.system("dpkg-reconfigure -fnoninteractive mythweb")


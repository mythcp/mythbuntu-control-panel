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
import os, string, logging, configparser, subprocess, time

from MythbuntuControlPanel.dictionaries import *

class MythPluginsPlugin(MCPPlugin):
    """A tool for enabling MythTV plugins"""

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
        list = get_frontend_plugin_dictionary(self)
        for item in list:
            self.dictionary_state[list[item]]=self.query_installed(item)
        #Web app launcher
        if os.path.isfile("/usr/share/applications/mythtv_web_app.desktop"):
            self.web_app_l_state=True
        else:
            self.web_app_l_state=False

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        #Load the detected dictionary
        for item in self.dictionary_state:
            item.set_active(self.dictionary_state[item])
        #Web app launcher
        self.webapp_checkbox.set_active(self.web_app_l_state)

    def on_web_app_select(self, widget, data=None):
        """Backend IP entry available if web app launcher selected"""
        if self.webapp_checkbox.get_active() and not self.web_app_l_state:
            be_state = subprocess.run(['systemctl', 'is-active', '--quiet', 'mythtv-backend']).returncode
            home = os.environ['HOME']
            self.backend_ip_entry.show()
            if be_state == 0:
                self.backend_ip_entry.set_text('localhost')
            elif os.path.isfile(home + '/.mythtv/config.xml'):
                import xml.etree.ElementTree as et
                tree = et.parse(home + '/.mythtv/config.xml')
                root = tree.getroot()
                host = root.find(".//Host").text
                self.backend_ip_entry.set_text(host)
        else:
            self.backend_ip_entry.hide()

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)
        #Installable items
        list = get_frontend_plugin_dictionary(self)
        for item in list:
            if list[item].get_active() != self.dictionary_state[list[item]]:
                if list[item].get_active():
                    self._markInstall(item)
                else:
                    self._markRemove(item)
        #Web app launcher
        web_app_l_state_now = self.webapp_checkbox.get_active()
        if self.web_app_l_state != web_app_l_state_now:
            if web_app_l_state_now:
                self._markReconfigureRoot("web_app_launcher",self.backend_ip_entry.get_text())
            else:
                self._markReconfigureRoot("web_app_launcher","remove")

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == "web_app_launcher":
                if reconfigure[item] != "remove":
                    host = reconfigure[item]
                    self.emit_progress("Checking if backend is reachable at location entered", 10)
                    time.sleep(2)
                    if host == 'Backend IP' or host == '':
                        self.emit_progress("IP address or host name was not entered (aborting)", 0)
                        time.sleep(2)
                    elif subprocess.run(["nc", "-z", host, "6543"]).returncode != 0:
                        self.emit_progress("Backend not reachable at location entered (aborting)", 0)
                        time.sleep(2)
                    else:
                        self.emit_progress("Creating MythTV Web App applications menu entry", 50)
                        time.sleep(2)
                        with open("/usr/share/applications/mythtv_web_app.desktop", 'w') as txt_file:
                            txt_file.write('[Desktop Entry]\n')
                            txt_file.write('Name=MythTV Web App\n')
                            txt_file.write('Comment=Web app for MythTV administration\n')
                            txt_file.write('Icon=system-component-application\n')
                            txt_file.write('Exec=xdg-open http://' + host + ':6544/\n')
                            txt_file.write('Terminal=false\n')
                            txt_file.write('Type=Application\n')
                            txt_file.write('Categories=GTK;Utility;AudioVideo;Audio;Video;\n')
                            txt_file.write('Actions=upcoming-recordings;backend-setup;program-guide\n')
                            txt_file.write('\n')
                            txt_file.write('[Desktop Action upcoming-recordings]\n')
                            txt_file.write('Name=Upcoming Recordings\n')
                            txt_file.write('Exec=xdg-open http://' + host + ':6544/dashboard/upcoming\n')
                            txt_file.write('\n')
                            txt_file.write('[Desktop Action backend-setup]\n')
                            txt_file.write('Name=Backend Setup\n')
                            txt_file.write('Exec=xdg-open http://' + host + ':6544/setupwizard/dbsetup\n')
                            txt_file.write('\n')
                            txt_file.write('[Desktop Action program-guide]\n')
                            txt_file.write('Name=Program Guide\n')
                            txt_file.write('Exec=xdg-open http://' + host + ':6544/dashboard/program-guide\n')
                else:
                    if os.path.isfile("/usr/share/applications/mythtv_web_app.desktop"):
                        os.remove("/usr/share/applications/mythtv_web_app.desktop")

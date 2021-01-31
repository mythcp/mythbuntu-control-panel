## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «roles» - MCP System Role selector plugin
#
# Modifications copyright (C) 2020, Ted (MythTV forums member heyted)
# Original copyright (C) 2009, Mario Limonciello, for Mythbuntu
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
from MythbuntuControlPanel.dictionaries import *
import shutil

class SystemRolesPlugin(MCPPlugin):
    """A tool for adjusting the role of a system"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "System Roles"
        information["icon"] = "gnome-monitor"
        information["ui"] = "tab_system_roles"
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it in the plugin's own internal structures"""
        #We can't really represent no backend or no frontend well yet
        self.no_back=True
        self.no_front=True

        #Dictionaries
        self.dictionary_state={}
        roles = get_role_dictionary(self)
        for item in roles:
            self.dictionary_state[roles[item]]=self.query_installed(item)
            if "backend" in item and self.dictionary_state[roles[item]]:
                self.no_back=False
            elif "frontend" in item and self.dictionary_state[roles[item]]:
                self.no_front=False  

        #corner case
        if self.dictionary_state[self.primary_backend_radio]:
            self.dictionary_state[self.secondary_backend_radio]=False

        if shutil.which("tv_sort"):
            self.xmltv_installed_state=True
        else:
            self.xmltv_installed_state=False
        if self.query_installed("openssh-server"):
            self.sshs_installed_state=True
        else:
            self.sshs_installed_state=False
        if not self.primary_backend_radio.get_active():
            self.xmltv_guide_data.set_sensitive(False)
        if shutil.which("hdhomerun_config"):
            self.hdhomerun_c_installed_state=True
        else:
            self.hdhomerun_c_installed_state=False
        if shutil.which("hdhomerun_config_gui"):
            self.hdhomerun_c_gui_installed_state=True
        else:
            self.hdhomerun_c_gui_installed_state=False

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        #Load the detected dictionary
        for item in self.dictionary_state:
            if self.dictionary_state[item]:
                item.set_active(True)

        #In case we don't have a front or back role
        self.no_backend_radio.set_active(self.no_back)
        self.no_frontend_radio.set_active(self.no_front)

        self.xmltv_guide_data.set_active(self.xmltv_installed_state)
        self.enablessh.set_active(self.sshs_installed_state)
        self.hdhomerun_config.set_active(self.hdhomerun_c_installed_state)
        self.hdhomerun_config_gui.set_active(self.hdhomerun_c_gui_installed_state)
        
    def on_backend_select(self, widget, data=None):
        """xmltv checkbox available if primary backend selected"""
        prim_backend_selected = self.primary_backend_radio.get_active()
        if prim_backend_selected:
            self.xmltv_guide_data.set_sensitive(True)
        else:
            self.xmltv_guide_data.set_active(False)
            self.xmltv_guide_data.set_sensitive(False)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)

        #backend unfortunately totally a corner case
        if self.primary_backend_radio.get_active() != self.dictionary_state[self.primary_backend_radio]:
            if self.primary_backend_radio.get_active():
                self._markInstall('mythtv-backend-master')
            else:
                self._markRemove('mythtv-backend-master')
                if not self.secondary_backend_radio.get_active():
                    self._markRemove('mythtv-backend')
        elif self.secondary_backend_radio.get_active() != self.dictionary_state[self.secondary_backend_radio]:
            if self.secondary_backend_radio.get_active():
                self._markInstall('mythtv-backend')
            else:
                self._markRemove('mythtv-backend')
        if self.frontend_radio.get_active() != self.dictionary_state[self.frontend_radio]:
            if self.frontend_radio.get_active():
                self._markInstall('mythtv-frontend')
            else:
                self._markRemove('mythtv-frontend')
        if self.xmltv_guide_data.get_active() != self.xmltv_installed_state:
            if self.xmltv_guide_data.get_active():
                self._markInstall('xmltv')
            else:
                self._markRemove('xmltv')
                self._markRemove('xmltv-util')
        if self.enablessh.get_active() != self.sshs_installed_state:
            if self.enablessh.get_active():
                self._markInstall('openssh-server')
            else:
                self._markRemove('openssh-server')
        if self.hdhomerun_config.get_active() != self.hdhomerun_c_installed_state:
            if self.hdhomerun_config.get_active():
                self._markInstall('hdhomerun-config')
            else:
                self._markRemove('hdhomerun-config')
        if self.hdhomerun_config_gui.get_active() != self.hdhomerun_c_gui_installed_state:
            if self.hdhomerun_config_gui.get_active():
                self._markInstall('hdhomerun-config-gui')
            else:
                self._markRemove('hdhomerun-config-gui')

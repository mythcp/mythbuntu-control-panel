## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «startup_behavior» - MCP startup options plugin
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
import os
import string
import re

class LoginPlugin(MCPPlugin):
    """A plugin for setting up automatic login"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Startup Behavior"
        information["icon"] = "desktop"
        information["ui"] = "tab_startup_behavior"
        self.user_count=0
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items on managed by this plugin
           and stores it into the plugin's own internal structures"""
        self.autostart_state=os.path.exists(os.environ['HOME'] + '/.config/autostart/mythtv.desktop')

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.enableautostartup.set_active(self.autostart_state)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)

        if self.autostart_state != self.enableautostartup.get_active():
            self._markReconfigureUser("autostartup",self.enableautostartup.get_active())

    def user_scripted_changes(self,reconfigure):
        """Local changes that can be performed by the user account.
           This function will be ran by the frontend"""
        for item in reconfigure:
            if item == 'autostartup':
                home = os.environ['HOME']
                if reconfigure[item]:
                    if not os.path.exists(home + '/.config/autostart'):
                        os.makedirs(home + '/.config/autostart')
                    if not os.path.exists(home + '/.config/autostart/mythtv.desktop'):
                        try:
                            os.symlink('/usr/share/applications/mythtv.desktop',home + '/.config/autostart/mythtv.desktop')
                        except OSError:
                            os.unlink(home + '/.config/autostart/mythtv.desktop')
                            os.symlink('/usr/share/applications/mythtv.desktop',home + '/.config/autostart/mythtv.desktop')
                elif os.path.exists(home + '/.config/autostart/mythtv.desktop'):
                    os.remove(home + '/.config/autostart/mythtv.desktop')

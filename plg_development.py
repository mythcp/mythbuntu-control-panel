## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «plg_development» - MCP unstable plugins provided for testing and development
#
# Copyright (C) 2020, Ted (MythTV forums member heyted)
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
import os, string, re, grp, getpass, shutil

class DevelopmentPlugin(MCPPlugin):
    """A plugin for enabling unstable plugins for testing and development"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Developmental*"
        information["icon"] = "gtk-dialog-warning"
        information["ui"] = "tab_development"
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it into the plugin's own internal structures"""
        self.enabledev_state=os.path.exists("/usr/share/mythbuntu/plugins/python/plg_mysql_config.py")

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.enableunstabletabs.set_active(self.enabledev_state)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)

        if self.enabledev_state != self.enableunstabletabs.get_active():
            self._markReconfigureRoot("developmental_modules",self.enableunstabletabs.get_active())

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == "developmental_modules":
                if reconfigure[item]:
                    dir1 = '/usr/share/mythbuntu/'
                    shutil.copyfile(dir1+'plg_mysql_config.py', dir1+'plugins/python/plg_mysql_config.py')
                    shutil.copyfile(dir1+'plg_plugins.py', dir1+'plugins/python/plg_plugins.py')
                    shutil.copyfile(dir1+'tab_mysql_config.ui', dir1+'plugins/ui/tab_mysql_config.ui')
                    shutil.copyfile(dir1+'tab_plugins.ui', dir1+'plugins/ui/tab_plugins.ui')
                else:
                    os.remove('/usr/share/mythbuntu/plugins/python/plg_mysql_config.py')
                    os.remove('/usr/share/mythbuntu/plugins/python/plg_plugins.py')
                    os.remove('/usr/share/mythbuntu/plugins/ui/tab_mysql_config.ui')
                    os.remove('/usr/share/mythbuntu/plugins/ui/tab_plugins.ui')

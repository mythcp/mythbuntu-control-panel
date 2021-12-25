## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «startup_behavior» - MCP startup options plugin
#
# Modifications copyright (C) 2020, Ted (MythTV Forum member heyted)
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
import re, grp, getpass

class LoginPlugin(MCPPlugin):
    """A plugin for startup options"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Startup Behavior"
        information["icon"] = "desktop"
        information["ui"] = "tab_startup_behavior"
        self.user_count=0
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it into the plugin's own internal structures"""
        home = os.environ['HOME']
        self.autostart_state=(os.path.exists(home + '/.config/autostart/mythtv.desktop') or 
        os.path.exists(home + '/.config/autostart/mythfrontend_d.desktop'))
        self.directstart_state=os.path.exists('/usr/share/applications/mythfrontend_d.desktop')
        self.ingroup_state=False #Current user is not in mythtv group unless found in group below
        current_user = getpass.getuser()
        groups = grp.getgrall()
        for group in groups:
            if group.gr_name == "mythtv" and current_user in group.gr_mem:
                self.ingroup_state=True #Current user is in mythtv group
                break

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.enableautostartup.set_active(self.autostart_state)
        self.enablestartdirect.set_active(self.directstart_state)
        if not self.ingroup_state:
            self.enableautostartup.set_sensitive(False)
            self.enablestartdirect.set_sensitive(False)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)
        if self.autostart_state != self.enableautostartup.get_active():
            self._markReconfigureUser("autostartup",self.enableautostartup.get_active())
        if self.directstart_state != self.enablestartdirect.get_active():
            self._markReconfigureRoot("directstart",(self.enablestartdirect.get_active(),
            self.enableautostartup.get_active(),os.environ['HOME']))

    def user_scripted_changes(self,reconfigure):
        """Local changes that can be performed by the user account.
           This function will be ran by the frontend"""
        for item in reconfigure:
            if item == 'autostartup':
                home = os.environ['HOME']
                if reconfigure[item]:
                    if os.path.exists(home + '/.config/autostart/mythtv.desktop'):
                        os.remove(home + '/.config/autostart/mythtv.desktop')
                    if os.path.exists(home + '/.config/autostart/mythfrontend_d.desktop'):
                        os.remove(home + '/.config/autostart/mythfrontend_d.desktop')
                    if not os.path.exists(home + '/.config/autostart'):
                        os.makedirs(home + '/.config/autostart')
                    if os.path.exists('/usr/share/applications/mythfrontend_d.desktop'):
                        dtfile = '/usr/share/applications/mythfrontend_d.desktop'
                        dtlink = '/.config/autostart/mythfrontend_d.desktop'
                    else:
                        dtfile = '/usr/share/applications/mythtv.desktop'
                        dtlink = '/.config/autostart/mythtv.desktop'
                    try:
                        os.symlink(dtfile,home + dtlink)
                    except OSError:
                        os.unlink(home + dtlink)
                        os.symlink(dtfile,home + dtlink)
                else:
                    if os.path.exists(home + '/.config/autostart/mythtv.desktop'):
                        os.remove(home + '/.config/autostart/mythtv.desktop')
                    if os.path.exists(home + '/.config/autostart/mythfrontend_d.desktop'):
                        os.remove(home + '/.config/autostart/mythfrontend_d.desktop')

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == "directstart":
                home = reconfigure[item][2]
                if reconfigure[item][0]:
                    if os.path.exists('/usr/share/applications/mythtv.desktop'):
                        desktop_file = open("/usr/share/applications/mythtv.desktop", "r")
                        new_desktop_file = ""
                        for line in desktop_file:
                            stripped_line = line.strip()
                            new_line = stripped_line.replace("Name=MythTV Frontend",
                            "Name=MythTV Direct Frontend")
                            new_line = new_line.replace("Exec=mythfrontend --service",
                            "Exec=mythfrontend.real --syslog local7")
                            new_desktop_file += new_line +"\n"
                        desktop_file.close()
                        writing_file = open("/usr/share/applications/mythfrontend_d.desktop", "w")
                        writing_file.write(new_desktop_file)
                        writing_file.close()
                        if reconfigure[item][1]:
                            if os.path.exists(home + '/.config/autostart/mythtv.desktop'):
                                os.remove(home + '/.config/autostart/mythtv.desktop')
                            if os.path.exists(home + '/.config/autostart/mythfrontend_d.desktop'):
                                os.remove(home + '/.config/autostart/mythfrontend_d.desktop')
                            try:
                                os.symlink('/usr/share/applications/mythfrontend_d.desktop',
                                home + '/.config/autostart/mythfrontend_d.desktop')
                            except OSError:
                                os.unlink(home + '/.config/autostart/mythfrontend_d.desktop')
                                os.symlink('/usr/share/applications/mythfrontend_d.desktop',
                                home + '/.config/autostart/mythfrontend_d.desktop')
                else:
                    if os.path.exists(home + '/.config/autostart/mythfrontend_d.desktop'):
                        os.remove(home + '/.config/autostart/mythfrontend_d.desktop')
                    if os.path.exists('/usr/share/applications/mythfrontend_d.desktop'):
                        os.remove('/usr/share/applications/mythfrontend_d.desktop')
                    if os.path.exists('/usr/share/applications/mythtv.desktop'):
                        if reconfigure[item][1]:
                            if os.path.exists(home + '/.config/autostart/mythtv.desktop'):
                                os.remove(home + '/.config/autostart/mythtv.desktop')
                            try:
                                os.symlink('/usr/share/applications/mythtv.desktop',
                                home + '/.config/autostart/mythtv.desktop')
                            except OSError:
                                os.unlink(home + '/.config/autostart/mythtv.desktop')
                                os.symlink('/usr/share/applications/mythtv.desktop',
                                home + '/.config/autostart/mythtv.desktop')

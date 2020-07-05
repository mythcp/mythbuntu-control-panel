## -*- coding: utf-8 -*-
#
# «plg_setup» - MCP misc system configuraton and launch backend setup
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
from shlex import quote
import os, string, re, grp, getpass, subprocess, shutil

class SetupPlugin(MCPPlugin):
    """A plugin for misc system configuraton and launching backend setup"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Setup"
        information["icon"] = "gnome-settings"
        information["ui"] = "tab_setup"
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it into the plugin's own internal structures"""
        self.adduser_state=False #Current user is not in mythtv group unless found in group below
        current_user = getpass.getuser()
        groups = grp.getgrall()
        for group in groups:
            if group.gr_name == "mythtv" and current_user in group.gr_mem:
                self.adduser_state=True #Current user is in mythtv group
                break
        self.linkconfig_state=os.path.exists(os.environ['HOME'] + '/.mythtv/config.xml')
        self.delaybackendstart_state=os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf')

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.addusertomythgrp.set_active(self.adduser_state)
        self.addlinktoconfig.set_active(self.linkconfig_state)
        status = subprocess.run(['systemctl', 'is-active', '--quiet', 'mythtv-backend']).returncode
        if status == 0:
            self.delaybackendstart.set_active(self.delaybackendstart_state)
        else:
            self.delaybackendstart.set_sensitive(False)
        if not shutil.which("mythtv-setup"):
            self.mythtv_setup_button.set_sensitive(False)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)

        adduserstate = self.addusertomythgrp.get_active()
        if self.adduser_state != adduserstate:
            current_user = quote(getpass.getuser())
            if adduserstate:
                self._markReconfigureRoot("user_in_mythtv_group",'adduser ' + current_user + ' mythtv')
            else:
                self._markReconfigureRoot("user_in_mythtv_group",'deluser ' + current_user + ' mythtv')
        if self.linkconfig_state != self.addlinktoconfig.get_active():
            self._markReconfigureUser("link_config_file",self.addlinktoconfig.get_active())
        if self.delaybackendstart_state != self.delaybackendstart.get_active():
            self._markReconfigureRoot("delay_backend_start",self.delaybackendstart.get_active())

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == "user_in_mythtv_group":
                subprocess.run(reconfigure["user_in_mythtv_group"], shell=True)
            if item == "delay_backend_start":
                if reconfigure[item]:
                    if not os.path.exists('/etc/systemd/system/mythtv-backend.service.d'):
                        os.makedirs('/etc/systemd/system/mythtv-backend.service.d')
                    with open('/etc/systemd/system/mythtv-backend.service.d/override.conf', 'w') as txt_file:
                        txt_file.write('[Unit]\n')
                        txt_file.write('After=network-online.target\n')
                        txt_file.write('Wants=network-online.target\n')
                        txt_file.write('[Service]\n')
                        txt_file.write('ExecStartPre=/bin/sleep 5')
                    subprocess.run(['systemctl', 'daemon-reload'])
                elif os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf'):
                    subprocess.run(['systemctl', 'revert', 'mythtv-backend'])

    def user_scripted_changes(self,reconfigure):
        """Local changes that can be performed by the user account.
           This function will be ran by the frontend"""
        for item in reconfigure:
            if item == 'link_config_file':
                home = os.environ['HOME']
                if reconfigure[item]:
                    if not os.path.exists(home + '/.mythtv'):
                        os.makedirs(home + '/.mythtv')
                    if os.path.exists('/etc/mythtv/config.xml'):
                        os.symlink('/etc/mythtv/config.xml',home + '/.mythtv/config.xml')
                elif os.path.exists(home + '/.mythtv/config.xml'):
                    os.remove(home + '/.mythtv/config.xml')

    def launch_setup(self,widget):
        """Stop the backend and run mythtv-setup"""
        status = subprocess.run(['systemctl', 'is-active', '--quiet', 'mythtv-backend']).returncode
        if status == 0:
            subprocess.run(['pkexec', 'systemctl', 'stop', 'mythtv-backend'])
        MCPPlugin.launch_app(self,widget,'mythtv-setup')

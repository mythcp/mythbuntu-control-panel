## -*- coding: utf-8 -*-
#
# «plg_setup» - MCP misc system configuraton and launch backend setup
#
# Copyright (C) 2020, Ted (MythTV Forum member heyted)
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
import os, string, re, grp, getpass, subprocess, shutil, time

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
        if os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf'):
            self.delaybackendstart_state=True
            conffile = open("/etc/systemd/system/mythtv-backend.service.d/override.conf", "r")
            self.delaymethod_state=0 #Basic
            for line in conffile:
                if 'wait-until-pingable' in line:
                    self.delaymethod_state=1 #Ping
                    position = line.find('wait-until-pingable')
                    self.pingentry_state = line[position+23:line.find(' ',position+23)] # Ping location text
                    break
                if 'hdhomerun' in line:
                    self.delaymethod_state=2 #HDHomeRun
                    break
            conffile.close()
        else:
            self.delaybackendstart_state=False
        self.stopbackend_state=False
        self.runsetupasmythtv_state=os.path.exists('/usr/share/polkit-1/actions/org.freedesktop.policykit.mythtv-setup.policy')

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.addusertomythgrp.set_active(self.adduser_state)
        self.addlinktoconfig.set_active(self.linkconfig_state)
        if self.delaybackendstart_state:
            self.enablenetworking.set_active(True)
            self.delaystartbox.set_active(self.delaymethod_state)
            if self.delaymethod_state == 1: # If delay method is Ping
                self.pingentry.set_text(self.pingentry_state) # Enter ping location text in text box
            else:
                self.pingentry.hide() # Hide ping location text box
        else:
            self.enablenetworking.set_active(False)
            self.pingentry.hide()
        self.stopbackend.set_active(self.stopbackend_state)
        self.runsetupasmythtv.set_active(self.runsetupasmythtv_state)
        status = subprocess.run(['systemctl', 'is-active', '--quiet', 'mythtv-backend']).returncode
        if not status == 0:
            self.enablenetworking.set_sensitive(False)
            self.stopbackend.set_sensitive(False)
        if not status == 0 or not self.delaybackendstart_state:
            self.delaystartbox.set_sensitive(False)
            self.pingentry.set_sensitive(False)
        if not shutil.which("mythtv-setup"):
            self.mythtv_setup_button.set_sensitive(False)
            self.runsetupasmythtv.set_sensitive(False)

    def on_network_select(self, widget, data=None):
        """Delay backend start method available if enable networking selected"""
        networking_selected = self.enablenetworking.get_active()
        if networking_selected:
            self.delaystartbox.set_sensitive(True)
            self.pingentry.set_sensitive(True)
        else:
            self.delaystartbox.set_sensitive(False)
            self.pingentry.set_sensitive(False)

    def on_delay_select(self, widget, data=None):
        """Ping entry available if ping method selected"""
        method_selected = self.delaystartbox.get_active_text()
        if method_selected == "Ping":
            self.pingentry.show()
        else:
            self.pingentry.hide()

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
        if self.delaybackendstart_state != self.enablenetworking.get_active():
            if self.enablenetworking.get_active():
                self._markReconfigureRoot("modify_networking","enable")
                self._markReconfigureRoot("backend_waits_for_network",self.delaystartbox.get_active_text())
                if self.delaystartbox.get_active_text() == "Ping":
                    self._markReconfigureRoot("ping_location",self.pingentry.get_text())
            else:
                self._markReconfigureRoot("modify_networking","disable")
        if self.delaybackendstart_state and self.enablenetworking.get_active(): # Networking was enabled and is still enabled
            reconfig_delay_method = False
            if self.delaymethod_state != self.delaystartbox.get_active(): # User selected different delay method
                reconfig_delay_method = True
            if self.delaymethod_state == 1 and self.delaystartbox.get_active() == 1: # The delay method was and still is Ping
                if self.pingentry_state != self.pingentry.get_text(): # User entered different ping location
                    reconfig_delay_method = True
            if reconfig_delay_method:
                self._markReconfigureRoot("modify_networking","delaymethod")
                self._markReconfigureRoot("backend_waits_for_network",self.delaystartbox.get_active_text())
                if self.delaystartbox.get_active_text() == "Ping":
                    self._markReconfigureRoot("ping_location",self.pingentry.get_text())
        if self.stopbackend_state != self.stopbackend.get_active():
            self._markReconfigureRoot("stop_backend",self.stopbackend.get_active())
        if self.runsetupasmythtv_state != self.runsetupasmythtv.get_active():
            self._markReconfigureRoot("run_setup_as_mythtv",self.runsetupasmythtv.get_active())

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == "user_in_mythtv_group":
                subprocess.run(reconfigure["user_in_mythtv_group"], shell=True)
            if item == "modify_networking":
                edit_mysql_cnf = False
                if reconfigure[item] == "enable" or reconfigure[item] == "delaymethod":
                    delaymethod = reconfigure["backend_waits_for_network"]
                    if delaymethod == "Basic":
                        self.emit_progress("Setting MythTV Backend to start after network is up", 10)
                        time.sleep(2)
                        if os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf'):
                            subprocess.run(['systemctl', 'revert', 'mythtv-backend'])
                        if not os.path.exists('/etc/systemd/system/mythtv-backend.service.d'):
                            os.makedirs('/etc/systemd/system/mythtv-backend.service.d')
                        with open('/etc/systemd/system/mythtv-backend.service.d/override.conf', 'w') as txt_file:
                            txt_file.write('[Unit]\n')
                            txt_file.write('After=network-online.target\n')
                            txt_file.write('Wants=network-online.target\n')
                            txt_file.write('[Service]\n')
                            txt_file.write('ExecStartPre=/bin/sleep 5')
                        subprocess.run(['systemctl', 'daemon-reload'])
                        if reconfigure[item] == "enable":
                            edit_mysql_cnf = True
                    if delaymethod == "Ping":
                        pinginput = reconfigure["ping_location"]
                        self.emit_progress("Attempting to ping device at " + pinginput, 10)
                        time.sleep(2)
                        pingable = subprocess.run(['/usr/share/mythbuntu/wait-until-pingable.py', pinginput, '15']).returncode
                        if pingable == 0:
                            self.emit_progress("Setting MythTV Backend to start after pinging device", 50)
                            time.sleep(2)
                            if os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf'):
                                subprocess.run(['systemctl', 'revert', 'mythtv-backend'])
                            if not os.path.exists('/etc/systemd/system/mythtv-backend.service.d'):
                                os.makedirs('/etc/systemd/system/mythtv-backend.service.d')
                            with open('/etc/systemd/system/mythtv-backend.service.d/override.conf', 'w') as txt_file:
                                txt_file.write('[Unit]\n')
                                txt_file.write('After=network.target\n')
                                txt_file.write('[Service]\n')
                                cmd = 'ExecStartPre=+/bin/bash -c "/usr/share/mythbuntu/wait-until-pingable.py ' + pinginput + ' 30"'
                                txt_file.write(cmd)
                            subprocess.run(['systemctl', 'daemon-reload'])
                            if reconfigure[item] == "enable":
                                edit_mysql_cnf = True
                        else:
                            self.emit_progress("Unable to ping device at provided location", 0)
                            time.sleep(2)
                    if delaymethod == "HDHomeRun":
                        self.emit_progress("Attempting to discover HDHomeRun device", 10)
                        time.sleep(2)
                        if not shutil.which("hdhomerun_config"):
                            self.emit_progress("hdhomerun_config is required but not currently installed", 0)
                            time.sleep(2)
                        elif not subprocess.run(['hdhomerun_config', 'discover']).returncode == 0:
                            self.emit_progress("Unable to find HDHomeRun device", 0)
                            time.sleep(2)
                        else:
                            self.emit_progress("Setting MythTV Backend to start after HDHomeRun is discoverable", 50)
                            time.sleep(2)
                            if os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf'):
                                subprocess.run(['systemctl', 'revert', 'mythtv-backend'])
                            if not os.path.exists('/etc/systemd/system/mythtv-backend.service.d'):
                                os.makedirs('/etc/systemd/system/mythtv-backend.service.d')
                            with open('/etc/systemd/system/mythtv-backend.service.d/override.conf', 'w') as txt_file:
                                txt_file.write('[Unit]\n')
                                txt_file.write('After=network.target\n')
                                txt_file.write('[Service]\n')
                                txt_file.write('ExecStartPre=/bin/bash -c "/usr/share/mythbuntu/hdhomerun-discover.py"')
                            subprocess.run(['systemctl', 'daemon-reload'])
                            if reconfigure[item] == "enable":
                                edit_mysql_cnf = True
                    if reconfigure[item] == "delaymethod":
                        self.emit_progress("Done", 100)
                        time.sleep(2)
                    if edit_mysql_cnf:
                        self.emit_progress("Enabling networking", 80)
                        time.sleep(2)
                        if os.path.exists('/etc/mysql/conf.d/mythtv.cnf'):
                            cnf_file = open("/etc/mysql/conf.d/mythtv.cnf", "r")
                            new_cnf_file = ""
                            for line in cnf_file:
                                stripped_line = line.strip()
                                if 'bind-address' in stripped_line:
                                    new_line = 'bind-address=*'
                                else:
                                    new_line = stripped_line
                                new_cnf_file += new_line +"\n"
                            cnf_file.close()
                            writing_file = open("/etc/mysql/conf.d/mythtv.cnf", "w")
                            writing_file.write(new_cnf_file)
                            writing_file.close()
                            self.emit_progress("Done", 100)
                            time.sleep(2)
                if reconfigure[item] == "disable":
                    if os.path.exists('/etc/systemd/system/mythtv-backend.service.d/override.conf'):
                        subprocess.run(['systemctl', 'revert', 'mythtv-backend'])
                    if os.path.exists('/etc/mysql/conf.d/mythtv.cnf'):
                        cnf_file = open("/etc/mysql/conf.d/mythtv.cnf", "r")
                        new_cnf_file = ""
                        for line in cnf_file:
                            stripped_line = line.strip()
                            if 'bind-address' in stripped_line:
                                new_line = '#' + stripped_line
                            else:
                                new_line = stripped_line
                            new_cnf_file += new_line +"\n"
                        cnf_file.close()
                        writing_file = open("/etc/mysql/conf.d/mythtv.cnf", "w")
                        writing_file.write(new_cnf_file)
                        writing_file.close()
            if item == "stop_backend":
                subprocess.run(['systemctl', 'stop', 'mythtv-backend'])
            if item == "run_setup_as_mythtv":
                if reconfigure[item]:
                    with open('/usr/share/polkit-1/actions/org.freedesktop.policykit.mythtv-setup.policy', 'w') as txt_file:
                        txt_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                        txt_file.write('<!DOCTYPE policyconfig PUBLIC\n')
                        txt_file.write(' "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"\n')
                        txt_file.write(' "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">\n')
                        txt_file.write('<policyconfig>\n')
                        txt_file.write('    <action id="org.freedesktop.policykit.pkexec.mythtv-setup">\n')
                        txt_file.write('    <description>Run mythtv-setup program</description>\n')
                        txt_file.write('    <message>Authentication is required to run mythtv-setup</message>\n')
                        txt_file.write('    <icon_name>mythtv</icon_name>\n')
                        txt_file.write('    <defaults>\n')
                        txt_file.write('        <allow_any>auth_admin</allow_any>\n')
                        txt_file.write('        <allow_inactive>auth_admin</allow_inactive>\n')
                        txt_file.write('        <allow_active>auth_admin</allow_active>\n')
                        txt_file.write('    </defaults>\n')
                        txt_file.write('    <annotate key="org.freedesktop.policykit.exec.path">/usr/bin/mythtv-setup</annotate>\n')
                        txt_file.write('    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>\n')
                        txt_file.write('    </action>\n')
                        txt_file.write('</policyconfig>')
                elif os.path.exists('/usr/share/polkit-1/actions/org.freedesktop.policykit.mythtv-setup.policy'):
                    os.remove('/usr/share/polkit-1/actions/org.freedesktop.policykit.mythtv-setup.policy')

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
        """Run mythtv-setup"""
        if getpass.getuser() == 'mythtv':
            MCPPlugin.launch_app(self,widget,'mythtv-setup')
        elif os.path.exists('/usr/share/polkit-1/actions/org.freedesktop.policykit.mythtv-setup.policy'):
            subprocess.run(['xhost', '+SI:localuser:mythtv'])
            MCPPlugin.launch_app(self,widget,"pkexec --user mythtv mythtv-setup")
            subprocess.run(['xhost', '-SI:localuser:mythtv'])
        else:
            MCPPlugin.launch_app(self,widget,'mythtv-setup')

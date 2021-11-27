## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «remotes» - IR and on-screen remotes configuration
#
# Copyright (C) 2021, Ted L (MythTV Forum member heyted)
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
import urllib3
import shutil, time, subprocess

class RemotesPlugin(MCPPlugin):
    """A tool for configuring remote controls"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Remotes"
        information["icon"] = "gtk-media-record"
        information["ui"] = "tab_remotes"
        MCPPlugin.__init__(self,information)

    def captureState(self):
        """Determines the state of the items managed by this plugin"""
        if shutil.which("ir-keytable"):
            self.ir_keytable_installed_state=True
        else:
            self.ir_keytable_installed_state=False

        if os.path.exists("/lib/udev/rc_keymaps"):
            self.default_keyc_fls = os.listdir('/lib/udev/rc_keymaps')
        else:
            self.default_keyc_fls = []
        self.default_keyc_fls = [dir_entry[:-5]
            for dir_entry in self.default_keyc_fls if dir_entry.endswith('.toml')]
        self.default_keyc_fls.sort()
        if len(self.default_keyc_fls) == 0:
            self.default_keyc_fls = ['None installed']
        self.keycode_d_box.get_model().clear()
        for item in self.default_keyc_fls:
            self.builder.get_object('keycode_d_box').append_text(item)

        self.home = os.environ['HOME']
        self.home_keyc_fls = []
        for item in os.listdir(self.home):
            if item.endswith('.toml'):
                self.home_keyc_fls.append(item[:-5])
        self.home_keyc_fls.sort()
        if len(self.home_keyc_fls) == 0:
            self.home_keyc_fls = ['None found in home folder']
        self.keycode_m_box.get_model().clear()
        for item in self.home_keyc_fls:
            self.builder.get_object('keycode_m_box').append_text(item)

        if os.path.exists("/usr/bin/mcpremote"):
            self.mcpremote_installed_state=True
        else:
            self.mcpremote_installed_state=False

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.enable_ir_kt.set_active(self.ir_keytable_installed_state)
        self.keycode_d_box.set_active(0)
        self.copy_dkcf.set_active(False)
        self.mod_kcf.set_active(False)
        self.keycode_m_box.set_active(0)
        self.temp_set_active.set_active(False)
        self.perm_set_active.set_active(False)
        self.enable_mcpr.set_active(self.mcpremote_installed_state)

    def on_kdcf_select(self, widget, data=None):
        self.copy_dkcf.set_active(True)

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)
        if self.enable_ir_kt.get_active() != self.ir_keytable_installed_state:
            if self.enable_ir_kt.get_active():
                self._markInstall('ir-keytable')
            else:
                self._markRemove('ir-keytable')
        if self.copy_dkcf.get_active():
            self._markReconfigureUser("copy_default_kcf",self.keycode_d_box.get_active_text())
        if self.mod_kcf.get_active() and self.keycode_m_box.get_active_text() != 'None found in home folder':
            self._markReconfigureUser("modify_kcf",self.keycode_m_box.get_active_text())
        if self.temp_set_active.get_active() and self.keycode_m_box.get_active_text() != 'None found in home folder':
            tmp_set_file_path = self.home + '/' + self.keycode_m_box.get_active_text() + ".toml"
            self._markReconfigureRoot("tmp_set_active",tmp_set_file_path)
        if self.perm_set_active.get_active() and self.keycode_m_box.get_active_text() != 'None found in home folder':
            perm_set_file_path = self.home + '/' + self.keycode_m_box.get_active_text() + ".toml"
            self._markReconfigureRoot("perm_set_active",perm_set_file_path)
        if self.enable_mcpr.get_active() != self.mcpremote_installed_state:
            if self.enable_mcpr.get_active():
                self._markReconfigureRoot("enable_mcpremote", self.home + '/.mythbuntu/mcpremote_amd64.deb')
            else:
                self._markReconfigureRoot("enable_mcpremote", False)

    def user_scripted_changes(self,reconfigure):
        """Local changes that can be performed by the user account.
           This function will be ran by the frontend"""
        for item in reconfigure:
            home = os.environ['HOME']
            if item == 'copy_default_kcf':
                def_kc_file = reconfigure["copy_default_kcf"] + ".toml"
                if os.path.exists('/lib/udev/rc_keymaps/'+def_kc_file):
                    shutil.copyfile('/lib/udev/rc_keymaps/'+def_kc_file, home+'/'+def_kc_file)
            if item == 'modify_kcf':
                mod_kc_file_nm = reconfigure["modify_kcf"] + ".toml"
                if os.path.exists(home+'/'+mod_kc_file_nm):
                    self.emit_progress("Modifying file", 50)
                    time.sleep(1)
                    to_replace = ("KEY_INFO","KEY_EPG","KEY_SELECT","KEY_RECORD","KEY_CHANNELUP",
                    "KEY_CHANNELDOWN","KEY_PLAY","KEY_PAUSE","KEY_REWIND","KEY_FASTFORWARD",
                    "KEY_PREVIOUS","KEY_NEXT","KEY_ZOOM","KEY_STOP","KEY_NUMERIC_1",
                    "KEY_NUMERIC_2","KEY_NUMERIC_3","KEY_NUMERIC_4","KEY_NUMERIC_5",
                    "KEY_NUMERIC_6","KEY_NUMERIC_7","KEY_NUMERIC_8","KEY_NUMERIC_9",
                    "KEY_NUMERIC_0","KEY_CLEAR","KEY_MENU","KEY_CANCEL","KEY_OK","KEY_DELETE",
                    "KEY_BACK","KEY_LAST","KEY_PLAYPAUSE","KEY_BLUE","KEY_RED","KEY_GREEN",
                    "KEY_YELLOW")
                    replace_with = ("KEY_I","KEY_S","KEY_ENTER","KEY_R","KEY_UP","KEY_DOWN",
                    "KEY_P","KEY_P","KEY_COMMA","KEY_DOT","KEY_PAGEUP","KEY_PAGEDOWN","KEY_W",
                    "KEY_ESC","KEY_1","KEY_2","KEY_3","KEY_4","KEY_5","KEY_6","KEY_7","KEY_8",
                    "KEY_9","KEY_0","KEY_ESC","KEY_M","KEY_ESC","KEY_ENTER","KEY_D","KEY_ESC",
                    "KEY_H","KEY_P","KEY_F5","KEY_F2","KEY_F3","KEY_F4")
                    kc_file = open(home+'/'+mod_kc_file_nm, "r")
                    mod_kc_file = ""
                    for line in kc_file:
                        stripped_line = line.strip()
                        for i in range(len(to_replace)):
                            if to_replace[i] in stripped_line:
                                new_line = stripped_line.replace(to_replace[i], replace_with[i])
                                break
                        else:
                            new_line = stripped_line
                        mod_kc_file += new_line +"\n"
                    kc_file.close()
                    writing_file = open(home+'/'+mod_kc_file_nm, "w")
                    writing_file.write(mod_kc_file)
                    writing_file.close()

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == 'tmp_set_active':
                if os.path.exists(reconfigure["tmp_set_active"]):
                    self.emit_progress("Setting keycode file active", 50)
                    time.sleep(2)
                    subprocess.run(['ir-keytable', '-c', '-w', reconfigure["tmp_set_active"]])
                    self.emit_progress("Done", 100)
                    time.sleep(1)
            if item == 'perm_set_active':
                if os.path.exists(reconfigure["perm_set_active"]):
                    self.emit_progress("Setting keycode file active", 30)
                    time.sleep(2)
                    subprocess.run(['ir-keytable', '-c', '-w', reconfigure["perm_set_active"]])
                    if os.path.exists('/etc/rc_keymaps'):
                        shutil.copyfile(reconfigure["perm_set_active"], "/etc/rc_keymaps/mcp_kcf.toml")
                        if os.path.exists('/etc/rc_maps.cfg'):
                            self.emit_progress("Modifying rc_maps.cfg", 60)
                            time.sleep(2)
                            cfg_file = open("/etc/rc_maps.cfg", "r")
                            mod_cfg_file = ""
                            for line in cfg_file:
                                stripped_line = line.strip()
                                if "driver table" in stripped_line:
                                    mod_cfg_file += stripped_line +"\n"
                                    new_line = "* * /etc/rc_keymaps/mcp_kcf.toml"
                                elif "mcp_kcf.toml" in stripped_line:
                                    continue
                                else:
                                    new_line = stripped_line
                                mod_cfg_file += new_line +"\n"
                            cfg_file.close()
                            writing_file = open("/etc/rc_maps.cfg", "w")
                            writing_file.write(mod_cfg_file)
                            writing_file.close()
                            self.emit_progress("Done", 100)
                            time.sleep(1)
                        else:
                            self.emit_progress("Expected file /etc/rc_maps.cfg not found", 0)
                            time.sleep(3)
                    else:
                        self.emit_progress("Expected path /etc/rc_keymaps not found", 0)
                        time.sleep(3)
            if item == 'enable_mcpremote':
                if reconfigure["enable_mcpremote"]:
                    self.emit_progress("Downloading MCP Remote", 20)
                    time.sleep(1)
                    deb_file = reconfigure["enable_mcpremote"]
                    url = 'https://github.com/mythcp/mcpremote/releases/latest/download/mcpremote_amd64.deb'
                    http = urllib3.PoolManager()
                    if os.path.exists(deb_file):
                        os.remove(deb_file)
                    try:
                        with open(deb_file, 'wb') as out:
                            r = http.request('GET', url, preload_content=False)
                            shutil.copyfileobj(r, out)
                    except:
                        if os.path.exists(deb_file):
                            os.remove(deb_file)
                        self.emit_progress('Unable to download MCP Remote', 0)
                        time.sleep(2)
                    if os.path.exists(deb_file):
                        self.emit_progress("Installing MCP Remote", 77)
                        time.sleep(1)
                        cmd = 'TMPDEB="$(mktemp)" && cp ' + deb_file + ' "$TMPDEB" && sudo dpkg -i "$TMPDEB"'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists("/usr/bin/mcpremote"):
                            self.emit_progress('MCP Remote successfully installed\nRestart MCP', 100)
                            time.sleep(3)
                        else:
                            self.emit_progress('Unable to install MCP Remote', 0)
                            time.sleep(2)
                else:
                    self.emit_progress('Removing MCP Remote', 50)
                    time.sleep(1)
                    subprocess.run(['dpkg', '-r', 'mcpremote'])
                    if os.path.exists("/usr/share/applications/mcpremote.desktop"):
                        os.remove("/usr/share/applications/mcpremote.desktop")
                    if os.path.exists("/usr/bin/mcpremote"):
                        os.remove("/usr/bin/mcpremote")
                    if os.path.exists("/usr/share/mcpremote/mcpremote.ui"):
                        shutil.rmtree("/usr/share/mcpremote")
                    if os.path.exists("/usr/share/mythbuntu/plugins/python/plg_mcp_remote.py"):
                        os.remove("/usr/share/mythbuntu/plugins/python/plg_mcp_remote.py")
                    if os.path.exists("/usr/share/mythbuntu/plugins/ui/tab_mcp_remote.ui"):
                        os.remove("/usr/share/mythbuntu/plugins/ui/tab_mcp_remote.ui")

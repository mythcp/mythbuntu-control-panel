## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «Mythbuntu Repos» - A Plugin for adding Mythbuntu Repos.
#
# Modifications copyright (C) 2020, Ted (MythTV Forum member heyted)
# Original copyright (C) 2009, Thomas Mashos, for Mythbuntu
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
################################################################################

from MythbuntuControlPanel.plugin import MCPPlugin
import os
import re
import subprocess
import urllib.request, urllib.error, urllib.parse
import shutil
import configparser
import time
import aptsources.sourceslist as sl

class MythbuntuReposPlugin(MCPPlugin):
    """A Plugin for adding MythTV Updates and MCP repos"""
    #
    #Load GUI & Calculate Changes
    #

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "Repositories"
        information["icon"] = "emblem-downloads"
        information["ui"] = "tab_repos"
        MCPPlugin.__init__(self, information)
        self.CONFIGFILE = "/etc/default/mythbuntu-repos"
        self.USERHOME = os.path.expanduser("~")
        if not os.path.isdir(self.USERHOME+"/.mythbuntu"):
            os.mkdir(self.USERHOME+"/.mythbuntu")
        if not os.path.isfile(self.USERHOME+"/.mythbuntu/repos.db"):
            if os.path.isfile("/usr/share/mythbuntu/repos.db"):
                shutil.copyfile("/usr/share/mythbuntu/repos.db", self.USERHOME+"/.mythbuntu/repos.db")
        if not os.path.isfile(self.USERHOME+"/.mythbuntu/repos.db"):
            try:
                self.downloadFile()
            except:
                pass
        self.config = configparser.ConfigParser()

    #Set mythtv versions
    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it into the plugin's own internal structures"""
        self.versions = []
        for line in open("/etc/lsb-release"):
            if "DISTRIB_CODENAME" in line:
                line = line.strip("\n")
                throwaway, distro = line.split("=")
        NumRepos = 0

        if os.path.isfile(self.USERHOME+"/.mythbuntu/repos.db"):
            self.versions = []
            for line in open(self.USERHOME+"/.mythbuntu/repos.db"):
                if distro in line:
                    line = line.strip("\n")
                    release, version = line.split("\t")
                    if not version in self.versions:
                        self.versions.append(version)
                    NumRepos += 1
                elif "MYTHTV_RELEASE" in line:
                    line = line.strip("\n")
                    VerName, self.CurVer = line.split("\t")
                elif "TRUNKPASS" in line:
                    line = line.strip("\n")
                    discard, self.TRUNKPASS = line.split("\t")
                elif "URL" in line:
                    line = line.strip("\n")
                    discard, self.DOWNLOADURL = line.split("\t")
            self.download_repo_db_label.hide()
            self.mythtv_updates_alignment.show()
            self.mythtv_updates_ckbox_alignment.show()
            self.mythtv_updates_label.show()
            self.mythtv_updates_checkbox.show()
            self.repobox.show()
            self.hseparator5.show()
            self.hseparator6.show()
            self.footer_alignment.show()
        if NumRepos == 0:
            self.versions.append('0')
            self.CurVer = '0'
            self.download_repo_db_label.show()
            self.mythtv_updates_alignment.hide()
            self.mythtv_updates_ckbox_alignment.hide()
            self.mythtv_updates_label.hide()
            self.mythtv_updates_checkbox.hide()
            self.repobox.hide()
            self.hseparator5.hide()
            self.hseparator6.hide()
            self.footer_alignment.hide()
            self.trunk_block.hide()
            self.DOWNLOADURL = 'https://raw.githubusercontent.com/mythcp/mythbuntu-control-panel/master/repos.db'
            
        self.changes = {}
        self.repobox.get_model().clear()
        for item in self.versions:
            self.builder.get_object('repobox').append_text(item)
        if os.path.exists(self.CONFIGFILE):
            self.config.read(self.CONFIGFILE)
        try:
            self.changes['MythTVUpdatesActivated'] = self.config.getboolean("cfg", "ActivateMythTVUpdates")
        except:
            self.changes['MythTVUpdatesActivated'] = False
        try:
            self.changes['MythTVUpdatesRepo'] = self.config.get("cfg", "MythTVRepo")
        except:            
            self.changes['MythTVUpdatesRepo'] = self.versions[0]
        #MCP Updates PPA current state
        sources = sl.SourcesList()
        self.MCPUpdatesActivated = False # False unless determined true below
        for entry in sources:
            if '/mythcp/mcp/' in entry.str() and entry.str()[0] != "#":
                self.MCPUpdatesActivated = True
                break

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self.mythtv_updates_checkbox.set_active(self.changes['MythTVUpdatesActivated'])
        self.repobox.set_sensitive(self.changes['MythTVUpdatesActivated'])
        try:
            self.repobox.set_active(self.versions.index(self.changes['MythTVUpdatesRepo']))
        except ValueError:
            self.repobox.set_active(0)
        self.trunk_pass_ok.hide()
        self.mcp_updates_checkbox.set_active(self.MCPUpdatesActivated)

    def on_mythtv_updates_checkbox_toggled(self, widget, data=None):
        """Show the repobox if this is checked"""
        widget_was_visible = self.mythtv_updates_checkbox.get_active()
        if widget_was_visible:
            self.repobox.set_sensitive(True)
        else:
            self.repobox.set_sensitive(False)

    def on_dev_password_entry_changed(self, widget, data=None):
        """Require a password for using trunk"""
        if self.dev_password_entry.get_text() == self.TRUNKPASS:
            self.trunk_pass_error.hide()
            self.trunk_pass_ok.show()
        else:
            self.trunk_pass_error.show()
            self.trunk_pass_ok.hide()

    def on_repobox_changed(self, widget, data=None):
        """Check the version to know if it's trunk"""
        if not self.repobox.get_active_text() == None:
            SELVER = self.convertVersion(self.repobox.get_active_text())
            if SELVER > self.CurVer:
                self.trunk_block.show()
            else:
                self.trunk_block.hide()

    def convertVersion(self, VERSION):
        """Remove the trailing .x if it exists"""
        if VERSION.endswith(".x"):
            VERSION = VERSION.strip(".x")
        return VERSION

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        MCPPlugin.clearParentState(self)
        SENDLIST = False
        SELVER = self.convertVersion(self.repobox.get_active_text())
        if self.mythtv_updates_checkbox.get_active() != self.changes['MythTVUpdatesActivated'] and self.mythtv_updates_checkbox.get_active() == False:
            self._markReconfigureRoot('MythTV-Updates-Activated', self.mythtv_updates_checkbox.get_active())
            SENDLIST = True
        if self.repobox.get_sensitive() == True:
            if self.repobox.get_active_text() != self.changes['MythTVUpdatesRepo'] or self.mythtv_updates_checkbox.get_active() != self.changes['MythTVUpdatesActivated']:
                if (SELVER > self.CurVer and self.dev_password_entry.get_text() == self.TRUNKPASS) or SELVER <= self.CurVer:
                    self._markReconfigureRoot('MythTV-Updates-Repo', self.repobox.get_active_text())
                    self._markReconfigureRoot('MythTV-Updates-Activated', self.mythtv_updates_checkbox.get_active())
                    SENDLIST = True
                elif self.mythtv_updates_checkbox.get_active() == False:
                    self._markReconfigureRoot('MythTV-Updates-Activated', self.mythtv_updates_checkbox.get_active())
        if SENDLIST == True:
            self._markReconfigureRoot('Repo-list', self.versions)
        if self.mcp_updates_checkbox.get_active() != self.MCPUpdatesActivated:
            self._markReconfigureRoot('MCP-Updates-Activated', self.mcp_updates_checkbox.get_active())

    def refresh_button_clicked(self, widget, data=None):
        """Download a new db file if requested"""
        self.downloadFile()
        self.captureState()
        self.applyStateToGUI()

    def downloadFile(self):
        """Download files"""
        try:
            url = self.DOWNLOADURL
        except:
            url = 'https://raw.githubusercontent.com/mythcp/mythbuntu-control-panel/master/repos.db'
        try:
            self.emit_progress("_", 0) #init (to do: remove)
            time.sleep(0.1)
            import urllib.request
            from urllib.error import HTTPError,URLError
            self.emit_progress("Refreshing available repos from server", 20)
            time.sleep(1)
            # Open the url
            f = urllib.request.urlopen(url)
            # Open our local file for writing
            local_repo_file = open(self.USERHOME+"/.mythbuntu/repos.db", "wb")
            #Write to our local file
            local_repo_file.write(f.read())
            local_repo_file.close()
            self.emit_progress("New DB file download finished", 100)
        #handle errors
        except HTTPError as e:
            print("HTTP Error:",e.code , url)
            self.emit_progress("HTTP Error: Failed to download new DB file", 0)
        except URLError as e:
            print("URL Error:",e.reason , url)
            self.emit_progress("URL Error: Failed to download new DB file", 0)
        time.sleep(2)
        self.emit_progress("_", 'done')

    #
    # Process selected activities
    #

    def root_scripted_changes(self, reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        self.emit_progress("Opening config file", 10)
        time.sleep(1)
        if os.path.exists(self.CONFIGFILE):
            self.config.read("/etc/default/mythbuntu-repos")
        else:
            self.config.add_section("cfg")
        if "Repo-list" in reconfigure:
            self.emit_progress("Removing old repositories", 40)
            time.sleep(1)
            for item in reconfigure["Repo-list"]:
                if item.endswith(".x"):
                    item = item.strip(".x")
                    subprocess.call(["apt-add-repository", "-r", "-y", "ppa:mythbuntu/"+item])
        if "MythTV-Updates-Activated" in reconfigure:
            self.emit_progress("Configuring MythTV Updates repo", 60)
            time.sleep(1)
            if reconfigure["MythTV-Updates-Activated"]:
                repo = reconfigure["MythTV-Updates-Repo"]
                self.config.set("cfg", "ActivateMythTVUpdates", "True")
                self.config.set("cfg", "MythTVRepo", repo)
                if repo.endswith(".x"):
                    repo = repo.strip(".x")
                subprocess.call(["apt-add-repository", "-y", "ppa:mythbuntu/"+repo])
            else:
                self.config.set("cfg", "ActivateMythTVUpdates", "False")
        #MCP Updates PPA:
        if "MCP-Updates-Activated" in reconfigure:
            self.emit_progress("Configuring MCP repo", 70)
            time.sleep(1)
            if reconfigure["MCP-Updates-Activated"]:
                subprocess.call(["apt-add-repository", "-y", "ppa:mythcp/mcp"])
                self.config.set("cfg", "ActivateMCPUpdates", "True")
            else:
                subprocess.call(["apt-add-repository", "-r", "-y", "ppa:mythcp/mcp"])
                self.config.set("cfg", "ActivateMCPUpdates", "False")
        with open('/etc/default/mythbuntu-repos', 'w', encoding='utf8') as configfile:
            self.emit_progress("Writing config file", 80)
            time.sleep(1)
            self.config.write(configfile)
        self.emit_progress("Done configuring repositories", 100)
        time.sleep(2)

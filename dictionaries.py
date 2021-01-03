# -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «dictionaries» - Manage list of all widget -> package matching
#
# This script:
# Modifications copyright (C) 2020, Ted (MythTV forums member heyted)
# Original copyright (C) 2008, Mario Limonciello, for Mythbuntu
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

import string
import subprocess

####################
# Type dictionaries: different installation types possible
def get_install_type_dictionary(self):
    list= {
        "Master Backend/Frontend" : self.master_be_fe,                         \
        "Slave Backend/Frontend"  : self.slave_be_fe,                          \
        "Master Backend"          : self.master_be,                            \
        "Slave Backend"           : self.slave_be,                             \
        "Frontend"                : self.fe,                                   \
        "Set Top Box"             : self.stb }
    return list

####################
#Plugin dictionaries: these are for managing a list of all possible plugins
####################
def get_frontend_plugin_dictionary(self):
    list = {
        "mytharchive": self.mytharchive_checkbox,                              \
        "mythbrowser": self.mythbrowser_checkbox,                              \
        "mythgame": self.mythgame_checkbox,                                    \
        "mythmusic": self.mythmusic_checkbox,                                  \
        "mythnews": self.mythnews_checkbox,                                    \
        "mythweather": self.mythweather_checkbox,                              \
        "mythzoneminder": self.mythzoneminder_checkbox }
    return list

def get_backend_plugin_dictionary(self):
    return { "mythweb": self.mythweb_checkbox }

####################
#Other dictionaries: these are for managing a list of all other apps
####################
def get_role_dictionary(self):
    list = {
        "mythtv-backend-master": self.primary_backend_radio,                   \
        "mythtv-backend":        self.secondary_backend_radio,                 \
        "mythtv-frontend":       self.frontend_radio }
    return list

def get_media_app_dictionary(self):
    list = {
        "mplayer": self.mplayer_checkbox,                                      \
        "xine-ui": self.xine_checkbox,                                         \
        "vlc":  self.vlc_checkbox }
    return list

def get_nonfree_dictionary(self):
    list = {
        "libdvdcss2": self.enable_libdvdcss2 }
    return list

def get_services_dictionary(self,sql_object=None):
    list = {
        "x11vnc": self.enablevnc,                                              \
        "samba": self.enablesamba,                                             \
        "nfs-kernel-server": self.enablenfs,                                   \
        "openssh-server": self.enablessh,                                      \
        "mysql-server": sql_object }
    return list

def get_graphics_dictionary():
    list = {}

    #NVIDIA Graphics detection
    try:
        from NvidiaDetector.nvidiadetector import NvidiaDetection
    except ImportError:
        return list

    nv = NvidiaDetection().selectDriver()
    if nv is not None:
        list["NVIDIA Graphics"]=nv
    return list

def get_tweak_dictionary(self):
    list = {
        "/etc/mysql/conf.d/mythtv-tweaks.cnf": self.enable_mysql_tweaks, \
        "/etc/cron.daily/optimize_mythdb": self.enable_mysql_repair}
    return list

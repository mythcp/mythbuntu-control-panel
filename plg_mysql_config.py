## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «mysql_config» - MCP MysQL Related configuration plugin
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
import re
import logging

from MythbuntuControlPanel.mysql import MySQLHandler
from MythbuntuControlPanel.dictionaries import get_tweak_dictionary

MYSQL_TXT='/etc/mythtv/mysql.txt'

MYTHTV_SETUP='/usr/bin/mythtv-setup'
OPTIMIZE_DATABASE="/usr/bin/x-terminal-emulator -e perl /usr/share/doc/mythtv-backend/contrib/maintenance/optimize_mythdb.pl"

class MySQLConfigurationPlugin(MCPPlugin):
    """A configuration tool for MySQL Related Connectivity"""

    def __init__(self):
        #Initialize parent class
        information = {}
        information["name"] = "MySQL*"
        information["icon"] = "gtk-network"
        information["ui"] = "tab_mysql_config"
        MCPPlugin.__init__(self,information)
        self.mysql=MySQLHandler()

    def captureState(self):
        """Determines the state of the items managed by this plugin
           and stores it into the plugin's own internal structures"""

        #Roles
        self.frontend=False
        self.mysql_service=False
        if self.query_installed('mythtv-backend-master'):
            #enable master backend and backend, disable frontend
            self.master=True
            self.backend=True
            if os.path.exists("/etc/mysql/conf.d/mythtv.cnf"):
                in_f=open("/etc/mysql/conf.d/mythtv.cnf")
                for line in in_f:
                    if re.compile("^bind-address").search(line):
                        self.mysql_service=True
                        break
                in_f.close()
        else:
            self.master=False
            self.backend=self.query_installed('mythtv-backend')

        if os.path.exists(os.path.join(os.environ['HOME'], '.mythtv', 'config.xml')):
            self.mysql.read_xml(os.path.join(os.environ['HOME'], '.mythtv', 'config.xml'))

        #Dictionaries
        self.dictionary_state={}
        list=get_tweak_dictionary(self)
        for item in list:
            self.dictionary_state[list[item]]=os.path.exists(item)

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""

        #Master
        if self.master:
            self.master_backend_vbox.show()
            if self.mysql_service:
                self.enablemysql.set_active(1)
            else:
                self.enablemysql.set_active(0)
        else:
            self.master_backend_vbox.hide()

        #Backend
        if self.backend:
            self.backend_vbox.show()
        else:
            self.backend_vbox.hide()

        #Connectivity
        config=self.mysql.get_config()
        self.security_entry.set_text(config["securitypin"])
        self.mysql_test_hbox.hide()

        #Dictionaries
        for item in self.dictionary_state:
            item.set_active(self.dictionary_state[item])

        self._incomplete=False

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        #Prepare for state capturing
        MCPPlugin.clearParentState(self)

        list=get_tweak_dictionary(self)
        for item in list:
            if list[item].get_active() != self.dictionary_state[list[item]]:
                self._markReconfigureRoot(item,list[item].get_active())

        if self.master:
            if self.mysql_service and self.enablemysql.get_active_text() == "Disable":
                #disable service
                self._markReconfigureRoot("mysql_service",False)
            if not self.mysql_service and self.enablemysql.get_active_text() == "Enable":
                #enable service
                self._markReconfigureRoot("mysql_service",True)
        else:
            config=self.mysql.get_config()
            if self.security_entry.get_text() != config["securitypin"]:
                self._markReconfigureUser("securitypin",self.security_entry.get_text())

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        for item in reconfigure:
            if item == "mysql_service":
                self.mysql.toggle_mysql_service_config(reconfigure[item])
                self.mysql.restart_mysql_service()
            elif item == "/etc/mysql/conf.d/mythtv-tweaks.cnf" or\
                 item == "/etc/cron.daily/optimize_mythdb":
                if reconfigure[item]:
                    import shutil
                    try:
                        if os.path.exists(item):
                            os.remove(item)
                        if item == "/etc/mysql/conf.d/mythtv-tweaks.cnf":
                            shutil.copy('/usr/share/mythbuntu/examples/mythtv-tweaks.dist',item)
                        else:
                            shutil.copy('/usr/share/doc/mythtv-backend/contrib/maintenance/optimize_mythdb.pl',item)
                            os.chmod(item,0o755)
                    except Exception as msg:
                        logging.warning("Exception when enabling %s, %s" % (item,msg))
                else:
                    try:
                        os.remove(item)
                    except Exception as msg:
                        logging.warning("Exception when disabling item %s, %s" % (item,msg))

    def user_scripted_changes(self, reconfigure):
        for item in reconfigure:
            if item == "securitypin":
                logging.debug("Updating MySQL config")
                #We don't actually have to modify this - if it was successful, it would have happened from the test.
                self.mysql.read_xml()
                if not os.path.exists(os.path.join(os.environ['HOME'],'.mythtv')):
                    os.makedirs(os.path.join(os.environ['HOME'],'.mythtv'))
                self.mysql.write_mysql_txt(os.path.join(os.environ['HOME'],'.mythtv','mysql.txt'))

    def do_connection_test(self,widget):
        """Performs a connectivity test to the backend's mysql server"""
        if widget is not None:
            self.mysql_test_hbox.show()
            result = self.mysql.do_connection_test(self.security_entry.get_text())
            if not result:
                self.pass_mysql.show()
                self.fail_mysql.hide()
                self._incomplete=False
                return
            self.pass_mysql.hide()
            self.fail_mysql.show()
            self._incomplete=True

    def launch_app(self,widget):
        """Launches an app defined in the glade file"""
        if widget.get_name() == 'mysql_tweak_button':
            MCPPlugin.launch_app(self,widget,OPTIMIZE_DATABASE)
        elif widget.get_name() == 'mythtv_setup_button':
            MCPPlugin.launch_app(self,widget,MYTHTV_SETUP)

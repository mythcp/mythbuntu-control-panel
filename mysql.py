# -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «mysql» - mythbuntu class for mysql mangling
#
# This script:
# Modifications copyright (C) 2020, Ted (MythTV forums member heyted)
# Original copyright (C) 2007-2010, Mario Limonciello, for Mythbuntu
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

import shutil
import os
import subprocess
import re
import string
import xml.dom.minidom


#pymysql isn't available yet.
#for now don't fail on import
try:
    import pymysql
except:
    pass

class MySQLHandler:
    """MySQL configuration, mangling, and activation class"""

    def __init__(self,config={"user":"mythtv","password":"mythtv","server":"localhost","database":"mythconverg","securitypin":"0000"}):
        self.user=config["user"]
        self.password=config["password"]
        self.server=config["server"]
        self.database=config["database"]
        self.securitypin=config["securitypin"]

    def _config_xml(self, file=None):
        """Reads in and parses and writes a config.xml from a number of places:
           1) /etc/mythtv/config.xml
           2) /usr/share/mythtv/config.xml
           Returns a dictionary filled with references that can be parsed or processed
        """
        dictionary={"doc": None, 'DBHostName': None, 'DBUserName': None, 'DBPassword': None, 'DBName': None, 'SecurityPin' : None}
        for file in [file, '/etc/mythtv/config.xml', '/usr/share/mythtv/config.xml' ]:
            if file and os.path.exists(file):
                dictionary["doc"]=xml.dom.minidom.parse(file)
                for tag in dictionary:
                    elements=dictionary["doc"].getElementsByTagName(tag)
                    if elements:
                        dictionary[tag]=elements[0]
                    elif tag != "doc":
                        dictionary[tag]=dictionary["doc"].createElement(tag)
                break
        return dictionary

    def write_xml(self,file):
        """Writes XML to a file"""
        dict=self._config_xml(file)
        if dict['DBHostName'].hasChildNodes():
            dict['DBHostName'].childNodes[0].replaceWholeText(self.server)
        else:
            node = dom.xml.minidom.createTextNode(self.server)
            dict['DBHostName'].appendChild(node)
        if dict['DBUserName'].hasChildNodes():
            dict['DBUserName'].childNodes[0].replaceWholeText(self.user)
        else:
            node = dom.xml.minidom.createTextNode(self.user)
            dict['DBUserName'].appendChild(node)
        if dict['DBPassword'].hasChildNodes():
            dict['DBPassword'].childNodes[0].replaceWholeText(self.password)
        else:
            node = dom.xml.minidom.createTextNode(self.password)
            dict['DBPassword'].appendChild(node)
        if dict['DBName'].hasChildNodes():
            dict['DBName'].childNodes[0].replaceWholeText(self.database)
        else:
            node = dom.xml.minidom.createTextNode(self.database)
            dict['DBName'].appendChild(node)
        if dict['SecurityPin'].hasChildNodes():
            dict['SecurityPin'].childNodes[0].replaceWholeText(self.securitypin)
        else:
            node = dom.xml.minidom.createTextNode(self.securitypin)
            dict['SecurityPin'].appendChild(node)

        dict["doc"].writexml(open(file, 'w'))

    def read_xml(self,file):
        dict=self._config_xml(file)
        if dict['DBHostName'].hasChildNodes():
            self.server = dict['DBHostName'].childNodes[0].data
        if dict['DBUserName'].hasChildNodes():
            self.user = dict['DBUserName'].childNodes[0].data
        if dict['DBPassword'].hasChildNodes():
            self.password = dict['DBPassword'].childNodes[0].data
        if dict['DBName'].hasChildNodes():
            self.database = dict['DBName'].childNodes[0].data
        if dict['SecurityPin'].hasChildNodes():
            self.securitypin = dict['SecurityPin'].childNodes[0].data

    def toggle_mysql_service_config(self,enable):
        """Enables and disables the mysql service on all interfaces"""
        if not os.path.exists("/etc/mysql/conf.d"):
            os.mkdir("/etc/mysql/conf.d")
        lines = None
        out_f = None
        found = False
        pattern = re.compile("^bind-address|^#bind-address")
        try:
            in_f = open("/etc/mysql/conf.d/mythtv.cnf")
            lines = in_f.readlines()
            in_f.close()
            out_f=open("/etc/mysql/conf.d/mythtv.cnf","w")
            for line in lines:
                if pattern.search(line) is None:
                    out_f.write(line)
                elif not found:
                    if enable:
                        out_f.write("bind-address=::\n")
                    else:
                        out_f.write("#bind-address=::\n")
                    found = True
            if not found:
                if enable:
                    out_f.write("bind-address=::\n")
                else:
                    out_f.write("#bind-address=::\n")
        except IOError:
            print("/etc/mysql/conf.d/mythtv.cnf not found")
            out_f=open("/etc/mysql/conf.d/mythtv.cnf","w")
            out_f.write("[mysqld]\n")
            if enable:
                out_f.write("bind-address=::\n")
            else:
                out_f.write("#bind-address=::\n")
        out_f.close()

    def restart_mysql_service(self):
        """Restarts MySQL service"""
        start_mysql = subprocess.Popen(["/usr/sbin/invoke-rc.d", "mysql", "restart"],stdout=subprocess.PIPE).communicate()[0]
        print(start_mysql)

    def update_config(self,config):
        """Sets up a new configuration based on the dict {user,pass,server,db,securitypin}"""
        self.user=config["user"]
        self.password=config["password"]
        self.server=config["server"]
        self.database=config["database"]
        self.securitypin=config["securitypin"]

    def get_config(self):
        """Returns our currently stored configuration"""
        return {"user":self.user,"password":self.password,"server":self.server,"database":self.database,"securitypin":self.securitypin}

    def reset_user_password(self,admin_pass,password):
        """Resets a user's password if it was forgotten"""
        commands = ["UPDATE user SET Password=PASSWORD('"+password+"') WHERE user=mythtv')",
        "FLUSH PRIVILEGES"]
        if self.run_mysql_commands(commands,mysql_user="root"):
            return "Successful"
        else:
            return "Failure"

    def run_mysql_commands(self,commands,mysql_user=None):
        """Runs mysql command(s) and returns the response"""
        if mysql_user is None:
            mysql_user = self.user
        try:
            db = pymysql.Connect(host=self.server, user=mysql_user, passwd=self.password,database=self.database)
            cursor = db.cursor()
            if type(commands) is list:
                for command in commands:
                    cursor.execute(command)
                    result = cursor.fetchone()
            elif type(commands) is str:
                result = cursor.execute(commands)
            else:
                print("Unknown type")
            cursor.close()
            db.close()
        except:
            result = False
        return result

    def do_connection_test(self, pin):
        """Tests to make sure that the backend is accessible"""
        try:
            import MythTV
        except ImportError:
            return False
        args = { 'SecurityPin' : pin }
        #figure out whether 0.24+ or 0.23
        try:
            method = getattr(MythTV, "MythDBBase")
        except AttributeError:
            method = getattr(MythTV, "MythDB")
        try:
            db_base = method(args=args)
        except Exception as e:
            return str(e)

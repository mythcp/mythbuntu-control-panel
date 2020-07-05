## -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «plugin» - The parent level class that all MCP plugins inherit from
#
# Modifications copyright (C) 2020, Ted (MythTV forums member heyted)
# Original copyright (C) 2009, Mario Limonciello, for Mythbuntu
#
# MCP is free software; you can redistribute it and/or modify it under
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

import logging
import sys
import os
import string
import traceback
import gi

#GUI Support
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

#Translation Support
from gettext import gettext as _

class MCPPluginLoader():
    """A class used for initializing all loadable plugins"""
    def __init__(self,plugin_root_path):
        self._instances = {}

        self.plugin_root_path = plugin_root_path
        self.plugin_path = plugin_root_path + '/python'

        if self.plugin_path not in sys.path:
            sys.path.insert(0, self.plugin_path)

    def reload_plugins(self):
        """Searches the path for all plugins asked for"""
        plugins=[]
        for obj in os.listdir(self.plugin_path):
            if '.py' in obj and '.pyc' not in obj:
                plugins.append(obj.split('.py')[0])

        for plugin in plugins:
            logging.debug(_("Importing plugin") + ": \t" + plugin)
            try:
                __import__(plugin, None, None, [''])
            except:
                logging.warning( _("Error importing plugin ") + plugin)
                traceback.print_exc()
                continue

    def find_plugin_classes(self):
        """Returns currently loaded plugin class types"""
        logging.debug(_("Found the following plugin classes:"))
        logging.debug(MCPPlugin.__subclasses__())

        return MCPPlugin.__subclasses__()

    def find_plugin_instances(self):
        """Returns all current instances of plugins"""
        result = []
        for plugin in self.find_plugin_classes():
            if not plugin in self._instances:
                try:
                    self._instances[plugin] = plugin()
                    self._instances[plugin]._set_root_path(self.plugin_root_path)
                except:
                    logging.warning( _("Error loading plugin ") + str(plugin))
                    traceback.print_exc()
                    continue
            result.append(self._instances[plugin])

        logging.debug(_("Found the following plugin instances:"))
        logging.debug(result)

        return result

class MCPPlugin(object):
    """An abstract class that defines what all plugins need to be able to do"""

    def __init__(self,information):
        """Initializes a parent MCP plugin.  Information is expected to be a dictionary containing
           these keys at a minimum:
            name: Name of the plugin
            icon: Icon shown for the plugin

            And one of these:
            ui: UI file used for the plugin"""
        if "name" not in information or \
           "icon" not in information or \
           "ui" not in information:
            self._abstract("__init__: information keys")
        self._information = information
        self._incomplete = False
        self.clearParentState()

    ###Helper functions###
    def _set_root_path(self,plugin_root_path):
        """Sets the path to load ui from"""
        self.plugin_root_path = plugin_root_path

    def _mark_array(self,array,item,value,action):
        """Internal helper function for modifying arrays"""
        if action:
            if type(array) is dict:
                array[item]=value
            else:
                array.append(item)
        else:
            if type(array) is dict:
                array.pop(item)
            else:
                for tmp in array:
                    if tmp == item:
                        array.remove(item)
                        return

    def _abstract(self, method):
        """Common error that gets raised if a plugin does not redefine
           a method that is supposed to be"""
        raise NotImplementedError("%s.%s does not implement %s" %
                                  (self.__class__.__module__,
                                   self.__class__.__name__, method))

    def updateCache(self,cache):
        """Updates the apt package cache"""
        self.pkg_cache=cache

    def getInformation(self,key=None):
        """Returns a standard information key"""
        if key is None:
            return self._information
        elif key == 'module':
            return self.__class__.__module__
        else:
            return self._information[key]

    def query_installed(self,package):
        """Determines if a single package is installed"""
        try:
            result = self.pkg_cache[package].current_ver
            if result == None:
                return False
            else:
                return True
        except KeyError:
            return False

    def getIncomplete(self):
        """Returns whether a plugin has been fully filled out"""
        return self._incomplete

    def launch_app(self,widget,data=None):
        """Launches an external application"""
        if widget is not None and data is not None:
            parent=widget.get_parent_window().get_toplevel()
            parent.hide()
            while Gtk.events_pending():
                Gtk.main_iteration()
            os.system(data)
            parent.show()
        else:
            self._abstract("launch_app")

    def insert_extra_widgets(self):
        """Litters the namespace with extra widgets if they exist.
           Generally these would be around for things like popup
           windows that are plugin specific"""

        ui_file = os.path.join(self.plugin_root_path, 'ui', self._information["ui"] + ".extra.ui")
        if os.path.exists(ui_file):
            logging.debug("Reading UI file: %s" % ui_file)
            self.builder.add_from_file(ui_file)

    def insert_subpage(self,notebook,buttonbox,handler):
        """Inserts a subtab into the notebook.  This assumes the file
        shares the same base name as the page you are looking for.
        Returns tuple: (name,tab) where tab is the numeric index of the
        tab in the GtkNoteBook"""

        # Button for the notebook widget
        label=Gtk.Label(label=self._information["name"])
        icon=Gtk.Image()
        icon.set_from_icon_name(self._information["icon"],3)
        button=Gtk.Button()
        button.set_alignment(0,0)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_focus_on_click(True)
        hbox=Gtk.HBox(spacing=2)
        hbox.pack_start(icon,False,False,0)
        hbox.pack_start(label,False,False,0)
        button.add(hbox)
        buttonbox.add(button)
        button.connect("clicked",handler)
        label.show()
        icon.show()
        hbox.show()
        button.show()

        # See http://faq.pyGtk.org/index.py?req=show&file=faq22.002.htp
        # for internationalisation support
        widget = None
        self.builder = Gtk.Builder()
        ui_file = os.path.join(self.plugin_root_path,'ui',self._information["ui"] + ".ui")
        logging.debug("Reading .ui file: %s" % ui_file)
        self.builder.add_from_file(ui_file)
        self.builder.connect_signals(self)
        for widget in self.builder.get_objects():
            if not isinstance(widget, Gtk.Widget):
                continue
            widget.set_name(Gtk.Buildable.get_name(widget))
            setattr(self, widget.get_name(), widget)
        #widget that we will append in the notebook
        widget = self.builder.get_object(self._information["ui"])

        logging.debug("Appending Widget: %s" % widget.get_name())
        notebook.append_page(widget,None)
        return (self._information["name"],notebook.page_num(widget))

    ###State machine of the plugin###
    def clearParentState(self):
        """Clears the state of the elements that were stored for between
           runs"""
        self._to_install     = []
        self._to_remove      = []
        self._to_reconfigure_root = {}
        self._to_reconfigure_user = {}
        self._request_update = False
        self._request_unauth = False

    def captureState(self):
        """Determines the state of the items on managed by this plugin
           and stores it into the plugin's own internal structures"""
        self._abstract("captureState")

    def compareState(self):
        """Determines what items have been modified on this plugin"""
        self._abstract("compareState")

    def applyStateToGUI(self):
        """Takes the current state information and sets the GUI
           for this plugin"""
        self._abstract("applyStateToGUI")

    ###Interfacing functions###
    def _markInstall(self,item,install=True):
        """Modifies the mark of an item to be installed"""
        self._mark_array(self._to_install,item,None,install)

    def _markRemove(self,item,remove=True):
        """Modifies the mark of an item to be removed"""
        self._mark_array(self._to_remove,item,None,remove)

    def _markUnauthenticatedPackages(self,unauth=True):
        """Toggles the bit to request an unauthenticated package to be installed"""
        self._request_unauth = unauth

    def _markUpdatePackageList(self,update=True):
        """Toggles the bit that requests a package list update at the end"""
        self._request_update = update

    def _markReconfigureRoot(self,item,value,reconfigure=True):
        """Modifies the mark of an item to be removed"""
        self._mark_array(self._to_reconfigure_root,item,value,reconfigure)

    def _markReconfigureUser(self,item,value,reconfigure=True):
        """Modifies the mark of an item to be removed"""
        self._mark_array(self._to_reconfigure_user,item,value,reconfigure)

    def getRawChanges(self):
        """Returns a tupple of raw arrays that can be assembled together"""
        return (self._to_install,self._to_remove,self._to_reconfigure_root, self._to_reconfigure_user,self._request_update,self._request_unauth)

    def summarizeChanges(self):
        """Returns a pretty summary of all management activities that will occur"""
        def summarizeDictionary(array,action):
            """Returns a summary of what's happening in array"""
            text=''
            if len(array) > 0:
                text+=action + " the following items:\n"
                for item in array:
                    text += '\t' + item + '\n'
            return text
        summary=summarizeDictionary(self._to_install,"Install") + \
                summarizeDictionary(self._to_remove, "Remove")  + \
                summarizeDictionary(self._to_reconfigure_root, "Reconfigure (as root)") + \
                summarizeDictionary(self._to_reconfigure_user, "Reconfigure (as user)")
        if self._request_update:
            summary = summary + "Request Package List Update\n"
        if self._request_unauth:
            summary = summary + "*** WARNING ***\n Unauthenticated Packages Will be Installed during this transaction.\n *** WARNING ***\n"
        if summary == '':
            summary=False
        return summary

    ###Non package-able changes###
    def emit_progress(self, string, pct):
        """Emits a progress event through the backend over dbus"""

    def root_scripted_changes(self,reconfigure):
        """System-wide changes that need root access to be applied.
           This function is ran by the dbus backend"""
        self._abstract("root_scripted_changes")

    def user_scripted_changes(self,reconfigure):
        """Local changes that can be performed by the user account.
           This function will be ran by the frontend."""
        self._abstract("user_scripted_changes")

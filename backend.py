#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Mythtbuntu Control Panel is a modified version of the original MCC program
# «backend» - Backend Manager.  Handles install actions that require root
#
# Modifications copyright (C) 2020, Ted (MythTV forums member heyted)
# Original work copyright (C) 2009, Mario Limonciello
#                         (C) 2008 Canonical Ltd.
#
# Original author:
#  - Mario Limonciello <superm1@ubuntu.com>
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

import logging, os, os.path, signal, sys

from gi.repository import GObject
import dbus
import dbus.service
import dbus.mainloop.glib

import getopt
import tempfile
import subprocess
import shutil
from shlex import split

from MythbuntuControlPanel.plugin import MCPPlugin

DBUS_BUS_NAME = 'com.mythbuntu.ControlPanel'

#Translation Support
from gettext import gettext as _

#--------------------------------------------------------------------#

class UnknownHandlerException(dbus.DBusException):
    _dbus_error_name = 'com.mythbuntu.ControlPanel.UnknownHandlerException'

class PermissionDeniedByPolicy(dbus.DBusException):
    _dbus_error_name = 'com.mythbuntu.ControlPanel.PermissionDeniedByPolicy'

class BackendCrashError(SystemError):
    pass

#--------------------------------------------------------------------#

def dbus_sync_call_signal_wrapper(dbus_iface, fn, handler_map, *args, **kwargs):
    '''Run a D-BUS method call while receiving signals.

    This function is an Ugly Hack™, since a normal synchronous dbus_iface.fn()
    call does not cause signals to be received until the method returns. Thus
    it calls fn asynchronously and sets up a temporary main loop to receive
    signals and call their handlers; these are assigned in handler_map (signal
    name → signal handler).
    '''
    if not hasattr(dbus_iface, 'connect_to_signal'):
        # not a D-BUS object
        return getattr(dbus_iface, fn)(*args, **kwargs)

    def _h_reply(result=None):
        global _h_reply_result
        _h_reply_result = result
        loop.quit()

    def _h_error(exception=None):
        global _h_exception_exc
        _h_exception_exc = exception
        loop.quit()

    loop = GObject.MainLoop()
    global _h_reply_result, _h_exception_exc
    _h_reply_result = None
    _h_exception_exc = None
    kwargs['reply_handler'] = _h_reply
    kwargs['error_handler'] = _h_error
    kwargs['timeout'] = 86400
    for signame, sighandler in list(handler_map.items()):
        dbus_iface.connect_to_signal(signame, sighandler)
    dbus_iface.get_dbus_method(fn)(*args, **kwargs)
    loop.run()
    if _h_exception_exc:
        raise _h_exception_exc
    return _h_reply_result

#--------------------------------------------------------------------#

class Backend(dbus.service.Object):
    '''Backend manager.

    This encapsulates all services calls of the backend. It
    is implemented as a dbus.service.Object, so that it can be called through
    D-BUS as well (on the /ControlPanel object path).
    '''
    DBUS_INTERFACE_NAME = 'com.mythbuntu.ControlPanel'

    #
    # D-BUS control API
    #

    def __init__(self):
        # cached D-BUS interfaces for _check_polkit_privilege()
        self.dbus_info = None
        self.polkit = None
        self.enforce_polkit = True

        #TODO:
        # debug support

    def run_dbus_service(self, timeout=None, send_usr1=False):
        '''Run D-BUS server.

        If no timeout is given, the server will run forever, otherwise it will
        return after the specified number of seconds.

        If send_usr1 is True, this will send a SIGUSR1 to the parent process
        once the server is ready to take requests.
        '''
        dbus.service.Object.__init__(self, self.bus, '/ControlPanel')
        main_loop = GObject.MainLoop()
        self._timeout = False
        if timeout:
            def _t():
                main_loop.quit()
                return True
            GObject.timeout_add(timeout * 1000, _t)

        # send parent process a signal that we are ready now
        if send_usr1:
            os.kill(os.getppid(), signal.SIGUSR1)

        # run until we time out
        while not self._timeout:
            if timeout:
                self._timeout = True
            main_loop.run()

    @classmethod
    def create_dbus_server(klass):
        '''Return a D-BUS server backend instance.
        '''
        import dbus.mainloop.glib

        backend = Backend()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        backend.bus = dbus.SystemBus()
        backend.dbus_name = dbus.service.BusName(DBUS_BUS_NAME, backend.bus)
        return backend

    #
    # Internal methods
    #

    def _reset_timeout(self):
        '''Reset the D-BUS server timeout.'''

        self._timeout = False

    def _check_polkit_privilege(self, sender, conn, privilege):
        '''Verify that sender has a given PolicyKit privilege.

        sender is the sender's (private) D-BUS name, such as ":1:42"
        (sender_keyword in @dbus.service.methods). conn is
        the dbus.Connection object (connection_keyword in
        @dbus.service.methods). privilege is the PolicyKit privilege string.

        This method returns if the caller is privileged, and otherwise throws a
        PermissionDeniedByPolicy exception.
        '''
        if sender is None and conn is None:
            # called locally, not through D-BUS
            return
        if not self.enforce_polkit:
            #yeah, i guess that sounds sensible to do..
            return

        # get peer PID
        if self.dbus_info is None:
            self.dbus_info = dbus.Interface(conn.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus/Bus', False), 'org.freedesktop.DBus')
        pid = self.dbus_info.GetConnectionUnixProcessID(sender)

        # query PolicyKit
        if self.polkit is None:
            self.polkit = dbus.Interface(dbus.SystemBus().get_object(
                'org.freedesktop.PolicyKit1',
                '/org/freedesktop/PolicyKit1/Authority', False),
                'org.freedesktop.PolicyKit1.Authority')
        try:
            # we don't need is_challenge return here, since we call with AllowUserInteraction
            (is_auth, _, details) = self.polkit.CheckAuthorization(
                    ('unix-process', {'pid': dbus.UInt32(pid, variant_level=1),
                     'start-time': dbus.UInt64(0, variant_level=1)}), 
                     privilege, {'': ''}, dbus.UInt32(1), '', timeout=600)
        except dbus.DBusException as e:
            if e._dbus_error_name == 'org.freedesktop.DBus.Error.ServiceUnknown':
                # polkitd timed out, connect again
                self.polkit = None
                return self._check_polkit_privilege(sender, conn, privilege)
            else:
                raise
        if not is_auth:
            logging.debug('_check_polkit_privilege: sender %s on connection %s pid %i is not authorized for %s: %s' %
                    (sender, conn, pid, privilege, str(details)))
            raise PermissionDeniedByPolicy(privilege)

    #
    # Internal API for calling from Handlers (not exported through D-BUS)
    #

        # none for now

    #
    # Client API (through D-BUS)
    #

    @dbus.service.method(DBUS_INTERFACE_NAME,
        in_signature='a{sa{sv}}s', out_signature='b', sender_keyword='sender',
        connection_keyword='conn')
    def scriptedchanges(self, plugin_dictionary, plugin_root_path, sender=None, conn=None):
        '''Processes changes that can't be represented by debian packages
           easily.  This function is sent a dictionary with key values of
           each plugin that has things to be processed.

           The matching data to each key plugin is a dictionary of
           {"item":"value"} of things to change within that particular
           key plugin.
        '''

        self._reset_timeout()
        self._check_polkit_privilege(sender, conn, 'com.mythbuntu.controlpanel.scriptedchanges')

        plugin_path = plugin_root_path + '/python'
        plugin_instances = {}

        logging.debug("scriptedchanges: using plugin_path of: %s" % plugin_path)
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        self.report_progress(_('Importing necessary plugins'),'0.0')
        for item in plugin_dictionary:
            #load plugin
            logging.debug("scriptedchanges: attempting to import plugin: %s" % item)
            try:
                __import__(item, None, None, [''])
            except:
                logging.warning("scriptedchanges: error importing plugin: %s " % item)
                del plugin_dictionary[item]
                continue

        self.report_progress(_('Instantiating necessary plugins'),'0.0')
        for item in MCPPlugin.__subclasses__():
            #instantiate
            logging.debug("scriptedchanges: attempting to instantiate plugin: %s" % item)
            try:
                plugin_instances[item] = item()
                plugin_instances[item].emit_progress=self.report_progress
            except:
                logging.warning("scriptedchanges: error instantiating plugin %s " % item)

        self.report_progress(_('Processing plugins'),'0.0')
        #process each plugin individually
        count=float(0)
        for plugin in plugin_dictionary:
            for instance in plugin_instances:
                if plugin_instances[instance].__class__.__module__ == plugin:
                    self.report_progress("Processing %s" % plugin, count/len(plugin_dictionary))
                    logging.debug("scriptedchanges: processing %s plugin " % plugin)
                    plugin_instances[instance].root_scripted_changes(plugin_dictionary[plugin])
                    count += 1
                    break

    @dbus.service.signal(DBUS_INTERFACE_NAME)
    def report_error(self, error_str, secondary=None):
        '''Reports an error to the UI'''
        return True

    @dbus.service.signal(DBUS_INTERFACE_NAME)
    def report_progress(self, progress, percent):
        '''Report package or script progress'''
        #if we are reporting progress, we shouldn't
        #ever let the dbus backend timeout
        self._reset_timeout()
        return True

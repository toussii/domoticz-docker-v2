# -*- coding: utf-8 -*-
#
#           Broadlink Python Plugin for Domoticz
#           Dev. Platform : Win10 x64 & Py 3.7.5 x86
#
#           Author:     zak45, 2020
#
#           1.0.0 :     Initial release
#
#           1.1.0 : 13/07/2020
#                   modify broadlink_connect : use of broadlink.gendevice()
#                   possibility to overwrite the default device type
#                   display only ini file name + domoticz idx and not full path in manage()
#           1.1.1 : 16/07/2020
#                   better support for mobile device & some code clean up
#           1.2.0 : 27/07/2020
#                   HTML code improved
#           1.3.0 : 04/08/2020
#                   module Broadlink v 0.14.1
#                   some code improvement
#           1.4.0 : 06/08/2020
#                   display customname on manage()
#                   check if Jquery (& ui) loaded, if not load them (admin)
#                   use broadlink.get_devices() to have devices list
#                   implement iframeResizer for dynamic iframe resize (autoresize:True)
#           1.4.1 : 07/08/2020
#                   added MyMemory link for translation (admin-language)
#                   added 'Scroll to top' feature
#           1.4.2 : 10/08/2020
#                   no overwrite lang file during update
#                   added link to cmd command for code send
#           1.5.0 : 27/08/2020
#                   show admin html page when enter base URL
#           1.6.0 : 29/08/2020
#                   learn IR/RF from Web Admin Page
#           1.6.1 : 01/09/2020
#                   Folder browse refactor
#           1.6.2 : 09/12/2020
#                   Modify sp3s device creation type
#           1.6.3 : 08/01/2021
#                   Work now in docker env: changed to 127.0.0.1 instead domoticz ip
#

"""
<plugin key="Broadlink" name="Broadlink with Kodi Remote" author="zak45" version="1.6.3"
    wikilink="http://www.domoticz.com/wiki/plugins/Broadlink.html"
    externallink="https://github.com/mjg59/python-broadlink">
    <description>
        <h2>Broadlink Python Plugin for Domoticz</h2><br/>
        <h2>Integrate Broadlink devices with Domoticz</h2>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>RM2/4 mini RM3 : RF / IR learning</li>
            <li>WebAdmin Page for management</li>
            <li>Control SP1/2/3 plugs</li>
            <li>Retrieve information from A1 device</li>
            <li>Manage your Multiplug</li>
            <li>Customizable & multi language plugin</li>
        </ul>
    </description>
    <params>
        <param field="Mode4" label="Broadlink IP Address" width="200px" required="true" default="192.168.1.X"/>
        <param field="Mode1" label="Mac" width="100px" required="true" default="AABBDDEEFF00"/>
        <param field="Mode3" label="Device Type" width="250px" required="true"  default="RM2">
            <options>
                <option label= "Remote Control RM2/3" value="RM2"/>
                <option label= "Remote Control RM2/3 with Temp" value="RM2T"/>
                <option label= "Remote Control mini RM2/3" value="RM2M"/>
                <option label= "Remote Control RM4" value="RM24"/>
                <option label= "Remote Control RM4 with Temp" value="RM24T"/>
                <option label= "Remote Control mini RM4" value="RM24M"/>
                <option label= "eSensor multi sensors A1" value="A1"/>
                <option label= "SmartPlug 1" value="SP1"/>
                <option label= "SmartPlug 2/3" value="SP2"/>
                <option label= "SmartPlug 3S" value="SP3S"/>
                <option label= "MultiPlug 1" value="MP1"/>
            </options>
        </param>
        <param field="Mode2" label="Folder to store ini files (RM2/3/4)" width="300px" required="true"
        default="<plugin home>"/>
        <param field="Address" label="Domoticz IP Address" width="200px" required="true" default="192.168.1.Y"/>
        <param field="Port" label="Domoticz port" width="50px" required="true" default="8080"/>
        <param field="Mode5" label="Listener port" width="50px" required="true" default="9000"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
                <option label="MS Visual Studio" value="999"/>
            </options>
        </param>
    </params>
</plugin>
"""
#
# Main Import
import uuid
import html
import json
import re
import traceback
import cgitb
import urllib.request
import urllib.parse
import urllib.error
import urllib.parse as urlparse
from urllib.parse import parse_qs
import ntpath

import Domoticz
import configparser
import datetime
import codecs
import subprocess
import socket
import os
import sys
import binascii
import struct
import time

#
import broadlink
#
from requests_toolbelt import MultipartDecoder

#
clear = False
autoresize = True
brodevices = broadlink.get_devices()
#
ISCONNECTED = False
NUMBERDEV = 9
BYPASS = False
TEMP = 0
LEARNEDCOMMAND = "None"
SENDCOMMAND = ""
LOADEDCOMMAND = ""
NBUPDATE = 1
CUSTOM = ""
REMOTECOMMAND = ""
STATE = True
STATEMP1 = {}
ENERGY = 0
UNIT = 0
REMOTEKEY = ''
REMOTETOSEND = ''
INFOLEVEL = 0
#
LANGDICT = {}
LANGTO = 'en'
CMD = ''
#
USEDPORT = False
HTTPSERVERCONN = None
HTTPCONNECTIONS = {}
HTTPCLIENT = None
#
DOMDATA = {}
URLKEY = str(uuid.getnode())
WEBROOT = True
DISPLAYPATH = ''
ADJUSTVALUE = 0
DEVICE = broadlink.rm(host=('', 80), mac=bytearray.fromhex(''), devtype=0x272a)
NEWPLUGIN = "no"


#
# find translation
# if no translation, put __ on start/end
#
def _(idata):
    origdata = idata

    if idata in LANGDICT:
        idata = LANGDICT[idata]

    else:

        if type(idata) is str:
            idata = '__' + origdata + '__'

        else:

            idata = origdata

    return idata


#
# Domoticz call back functions
#

# Executed once at HW creation/ update. Can create up to 255 devices.
def onStart():
    global NUMBERDEV, NBUPDATE, INFOLEVEL, CMD, LANGTO, USEDPORT, HTTPSERVERCONN, ADJUSTVALUE, DISPLAYPATH, NEWPLUGIN

    cgitb.enable(logdir=Parameters['HomeFolder'] + 'log/')

    if Parameters["Mode6"] == "999":
        INFOLEVEL = 999
        try:
            import debugpy
            Domoticz.Debugging(62)
            Domoticz.Log('Waiting for MS Visual Studio remote debugger connection ....')
            debugpy.configure(python='C:\Program Files (x86)\Python38-32\python.exe')
            debugpy.listen(('0.0.0.0', 5678))
            debugpy.wait_for_client()
            debugpy.breakpoint()

        except (ValueError, Exception):
            Domoticz.Error(_('Not able to load debug module'))

    elif Parameters["Mode6"] != "0":
        Domoticz.Debugging(int(Parameters["Mode6"]))
        INFOLEVEL = 9
        dump_config_to_log()

    #
    # default ini folder
    if Parameters["Mode2"] == '<plugin home>':
        Parameters["Mode2"] = Parameters['HomeFolder'] + "ini/"

    if not Parameters["Mode2"].endswith('/'):
        Parameters["Mode2"] += "/"

    # select command to launch depend of OS
    if sys.platform.startswith('win32'):
        CMD = "scr/dombr.cmd"
        Parameters["Mode2"] = Parameters["Mode2"].replace("\\", "/")

    else:

        CMD = "scr/dombr.sh"

    DISPLAYPATH = Parameters["HomeFolder"]
    #
    # Language file
    LANGTO = Settings["Language"]
    if load_lang():
        Domoticz.Log(_('Language loaded for  : {} ').format(LANGTO))

    else:

        Domoticz.Error(_('Language file is missing for : {}').format(LANGTO))
    #
    # Run web server
    if is_open(Parameters['Address'], Parameters["Mode5"]):
        USEDPORT = True
        Domoticz.Error(_('Port already in use'))

    else:

        HTTPSERVERCONN = Domoticz.Connection(Name="BROWebServer", Transport="TCP/IP", Protocol="HTTP",
                                             Port=Parameters["Mode5"])
        HTTPSERVERCONN.Listen()
        Domoticz.Log(_("Listen on BROWebServer - Port: {}").format(Parameters['Mode5']))
        #
        if INFOLEVEL > 1:
            Domoticz.Log(_('Hardware ID: {} ').format(str(Parameters['HardwareID'])))
    #
    # Create devices : device number 1 used mainly for status
    if 'RM2' in Parameters["Mode3"]:
        if 1 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + '-' + _('Status'), Unit=1, Type=17, Image=17, Switchtype=17,
                            Used=1).Create()
        if 2 not in Devices:
            options = {"LevelActions": "||||",
                       "LevelNames": "Off|" + _('Learn') + "|" + _('Test') + "|" + _('Save') + "|" + _('Reset'),
                       "LevelOffHidden": "true",
                       "SelectorStyle": "0"
                       }
            Domoticz.Device(Name=_("IR Commands"), Unit=2, TypeName="Selector Switch", Switchtype=18, Image=12,
                            Options=options, Used=1).Create()

        if 3 not in Devices and (Parameters["Mode3"] != 'RM2M' or Parameters["Mode3"] != 'RM24M'):
            options = {"LevelActions": "|||||",
                       "LevelNames": "Off|" + _('Sweep') + "|" + _('Learn') + "|" + _('Test') + "|" + _('Save') + "|" +
                                     _('Reset'),
                       "LevelOffHidden": "true",
                       "SelectorStyle": "0"
                       }
            Domoticz.Device(Name=_("RF Commands"), Unit=3, TypeName="Selector Switch", Switchtype=18, Image=12,
                            Options=options, Used=1).Create()

    if Parameters["Mode3"] == 'RM2T' or Parameters["Mode3"] == 'RM24T':
        if 4 not in Devices:
            Domoticz.Device(Name=_("Temperature"), Unit=4, TypeName="Temperature", Used=1).Create()

        adjust_value(4)

    elif Parameters["Mode3"] == 'SP1' or Parameters["Mode3"] == 'SP2' or Parameters["Mode3"] == 'SP3S':
        if 1 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]), Unit=1, TypeName="Switch", Image=1, Used=1).Create()
        if Parameters["Mode3"] == 'SP3S':
            if 2 not in Devices:
                Domoticz.Device(Name=str(Parameters["Mode3"]), Unit=2, TypeName="Usage", Used=1).Create()
            if 3 not in Devices:
                Domoticz.Device(Name=str(Parameters["Mode3"]), Unit=3, Type=243, Subtype=29, Switchtype=0,
                                Used=1).Create()
            if 4 not in Devices:
                Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Light'), Unit=4, TypeName="Switch", Used=1).Create()
        else:
            if 2 not in Devices:
                Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Light'), Unit=2, TypeName="Switch", Used=1).Create()

    elif Parameters["Mode3"] == 'A1':
        if 1 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Status'), Unit=1, Type=17, Image=17, Switchtype=17,
                            Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Temperature'), Unit=2, TypeName="Temperature",
                            Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Humidity'), Unit=3, TypeName="Humidity", Used=1).Create()
        if 4 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Air Quality'), Unit=4, TypeName="Air Quality",
                            Used=1).Create()
        if 5 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Noise'), Unit=5, TypeName="Sound Level", Used=1).Create()
        if 6 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Light'), Unit=6, TypeName="Illumination",
                            Used=1).Create()

        adjust_value(2)

    elif Parameters["Mode3"] == 'MP1':
        if 1 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('Status'), Unit=1, TypeName="Switch", Image=9,
                            Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('plug') + '1', Unit=2, TypeName="Switch", Image=1,
                            Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('plug') + '2', Unit=3, TypeName="Switch", Image=1,
                            Used=1).Create()
        if 4 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('plug') + '3', Unit=4, TypeName="Switch", Image=1,
                            Used=1).Create()
        if 5 not in Devices:
            Domoticz.Device(Name=str(Parameters["Mode3"]) + _('plug') + '4', Unit=5, TypeName="Switch", Image=1,
                            Used=1).Create()

    dump_config_to_log()
    Domoticz.Heartbeat(30)

    if 'RM2' in Parameters["Mode3"]:
        if not os.path.exists(Parameters["Mode2"] + "import"):
            os.makedirs(Parameters["Mode2"] + "import")
        if not os.path.exists(Parameters["Mode2"] + "remote"):
            os.makedirs(Parameters["Mode2"] + "remote")

        mpath = str(Parameters["Mode2"]) + "remote/" + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + \
            "-" + str('{:03d}'.format(1)) + ".ini"

        header = "[Custom]\ncommand = 0,"
        if not os.path.exists(mpath):
            try:
                with open(mpath, 'w', encoding='utf-8') as fp:
                    fp.write(header)
                Domoticz.Log(_('Ini file for remote controller created: {}').format(mpath))

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Error to create ini file for remote controller : {}').format(mpath))

        gen_remote()

        if 2 in Devices:
            update_device(2, 0, 'Off')
        if 3 in Devices:
            update_device(3, 0, 'Off')

    Domoticz.Log(_("Plugin Device count start on : {}").format(str(NUMBERDEV)))

    #
    # Verify if plugin need to be updated
    #
    checkver()

    #
    # Device file parameters
    #
    dev = ''
    devfile = Parameters['HomeFolder'] + "log/" + str(Parameters['HardwareID']) + Parameters['Mode3'] + ".txt"
    try:
        if not os.path.exists(devfile):
            if 'RM24' in Parameters["Mode3"]:
                dev = "0x51da" + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            elif 'RM2' in Parameters["Mode3"]:
                dev = "0x2712" + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            elif Parameters["Mode3"] == 'A1':
                dev = "0x2714" + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            elif Parameters["Mode3"] == 'SP1':
                dev = "0" + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            elif Parameters["Mode3"] == 'SP2' or Parameters["Mode3"] == 'SP3S':
                dev = "0x2711" + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            elif Parameters["Mode3"] == 'MP1':
                dev = "0x4EB5" + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]

            with open(devfile, 'w', encoding='utf-8') as fp:
                fp.write(dev)
            Domoticz.Log(_('Command line file created: {}').format(devfile))

        else:

            with open(devfile, 'r', encoding='utf-8') as fp:
                infile = fp.read().split(' ')
                dev = infile[0] + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            with open(devfile, 'w', encoding='utf-8') as fp:
                fp.write(dev)
            Domoticz.Log(_('Command line file updated: {}').format(devfile))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Error to create device file : {}').format(devfile))

    Domoticz.Log(_("Connecting to: {} : {}").format(Parameters["Mode4"], Parameters["Mode1"]))

    #
    # Set to default state
    #
    if 'RM2' in Parameters["Mode3"] or Parameters["Mode3"] == 'A1':
        if not broadlink_connect():
            update_device(1, 0, 'Off')

        else:

            update_device(1, 1, 'On')

    else:

        if broadlink_connect() and check_power():
            if STATE:
                update_device(1, 1, 'On')
            #                if (Parameters["Mode3"] == 'MP1'):
            #                    AllPlugOn()
            else:

                update_device(1, 0, 'Off')
        #                if (Parameters["Mode3"] == 'MP1'):
        #                    AllPlugOff()
        else:

            update_device(1, 0, 'Off')
    #            if (Parameters["Mode3"] == 'MP1'):
    #                    AllPlugOff()

    #
    # Main iframe definition
    #
    iframe = '''
        <iframe name="adminframe"
'''
    if autoresize:
        iframe += '''
         onload="iFrameResize({log:false,checkOrigin:false,warningTimeout:0,minHeight:600})"
'''
    iframe += '''
        src="http://''' + Parameters["Address"] + ''':''' + Parameters["Mode5"] + '''/manage?key=''' + URLKEY + '''" 
                width="100%" height="600" frameborder="0" style="border:0" allowfullscreen >
        </iframe>
'''
    #
    # Create main admin HTML page
    #
    adminfile = htmladmin('WebAdmin Page', iframe)
    html_file = Parameters['StartupFolder'] + 'www/templates/Broadlink-' + Parameters['Mode3'] + '-' + \
        str(Parameters["HardwareID"]) + '.html'

    if os.path.isdir(Parameters['StartupFolder'] + 'www/templates/'):
        try:
            with open(html_file, 'w', encoding='utf-8') as fp:
                fp.write(adminfile)
            Domoticz.Log(_('Admin html file created: {}').format(html_file))

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error to create admin html file : {}').format(html_file))

    else:

        Domoticz.Error(_('Error to found www/templates for html file : {}').format(html_file))

    #
    # Exit if port not available else download remote plugin file for version test
    #
    if USEDPORT:
        Domoticz.Error(_('We cannot continue ...'))
        onStop()

    else:

        start_shell('remotePlugin')

    return


# executed each time we click on device with domoticz GUI
def onCommand(iunit, command, level, hue):
    global SENDCOMMAND, LEARNEDCOMMAND, ISCONNECTED, CUSTOM

    Domoticz.Log("onCommand called for Unit " + str(iunit)
                 + ": Parameter '" + str(command)
                 + "', Level: " + str(level)
                 + " , Connected : " + str(ISCONNECTED)
                 )
    command = command.strip()
    if command == 'Set Level':
        if 'RM2' in Parameters["Mode3"]:
            if iunit == 2:  # Command selector for IR
                if level == 10:
                    LEARNEDCOMMAND = "None"
                    CUSTOM = "IR"
                    update_device(1, 1, _('Learn IR command'))
                    update_device(2, 1, '10')
                    start_shell('learnir')
                elif level == 20:
                    update_device(2, 1, '20')
                    SENDCOMMAND = LEARNEDCOMMAND
                    if LEARNEDCOMMAND == "None":
                        Domoticz.Log(_('Nothing to send'))
                        update_device(2, 0, 'Off')

                    else:

                        send()
                elif level == 30:
                    if LEARNEDCOMMAND == "None":
                        Domoticz.Log(_('Nothing to save'))

                    else:

                        if loop_ini():
                            update_device(1, 1, _('Ini created'))
                            update_device(2, 0, 'Off')
                            LEARNEDCOMMAND = "None"
                elif level == 40:
                    if LEARNEDCOMMAND == "None":
                        Domoticz.Log(_('Nothing to reset'))
                    reset()

                else:

                    Domoticz.Error(_('unknown level command'))

            elif iunit == 3:  # Command selector for RF
                if level == 10:
                    update_device(1, 1, _('Wait for sweep...'))
                    update_device(3, 1, '10')
                    start_shell('sweep')
                elif level == 20:
                    update_device(3, 1, '20')
                    if DEVICE.check_frequency():
                        CUSTOM = "RF"
                        update_device(1, 1, _('Learn RF command'))
                        start_shell('learnrf')

                    else:

                        Domoticz.Log(_('Sweep first'))
                        update_device(3, 0, 'Off')
                elif level == 30:
                    SENDCOMMAND = LEARNEDCOMMAND
                    if LEARNEDCOMMAND == "None":
                        Domoticz.Log(_('Nothing to send'))

                    else:

                        send()
                elif level == 40:
                    if LEARNEDCOMMAND == "None":
                        Domoticz.Log(_('Nothing to save'))

                    else:

                        update_device(3, 1, '40')
                        if loop_ini():
                            update_device(1, 1, _('Ini created'))
                            update_device(3, 1, '20')
                            LEARNEDCOMMAND = "None"
                elif level == 50:
                    if LEARNEDCOMMAND == "None":
                        Domoticz.Log(_('Nothing to reset'))
                    update_device(3, 1, '50')
                    reset()

                else:

                    Domoticz.Error(_('unknown level command'))

            else:

                Domoticz.Error(_('Unit unknown'))

    elif command == 'On':

        if (iunit == 1 and (
                Parameters['Mode3'] == 'SP1' or Parameters['Mode3'] == 'SP2' or Parameters['Mode3'] == 'SP3S')):
            try:
                DEVICE.set_power(True)
                update_device(iunit, 1, 'On')

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Error to put "ON" SP1/SP2/SP3'))
                ISCONNECTED = False
        elif ((iunit == 2 or iunit == 4) and (
                Parameters['Mode3'] == 'SP1' or Parameters['Mode3'] == 'SP2' or Parameters['Mode3'] == 'SP3S')):
            try:
                DEVICE.set_nightlight(True)
                update_device(iunit, 1, 'On')

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Error to put "on" light for SPx'))
                ISCONNECTED = False
        elif Parameters['Mode3'] == 'MP1':
            if 1 < iunit < 6:
                try:
                    DEVICE.set_power(iunit - 1, True)
                    update_device(iunit, 1, 'On')

                except (ValueError, Exception):
                    Domoticz.Error(traceback.format_exc())
                    Domoticz.Error(_('Error to put "ON" MP1 for plug : {}').format(str(iunit - 1)))

        else:

            if 'RM2' in Parameters["Mode3"]:
                if iunit == 1:
                    if ISCONNECTED:
                        update_device(1, 1, 'On')

                    else:

                        update_device(1, 0, 'Off')

                else:

                    gen_command(iunit)

            else:

                Domoticz.Error(_('Unknown command'))

    elif command == 'Off':

        if (iunit == 1 and (
                Parameters['Mode3'] == 'SP1' or Parameters['Mode3'] == 'SP2' or Parameters['Mode3'] == 'SP3S')):
            try:
                DEVICE.set_power(False)
                update_device(iunit, 0, 'Off')

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Error to put Off SP1/SP2/SP3'))
                ISCONNECTED = False
        elif ((iunit == 2 or iunit == 4) and (
                Parameters['Mode3'] == 'SP1' or Parameters['Mode3'] == 'SP2' or Parameters['Mode3'] == 'SP3S')):
            try:
                DEVICE.set_nightlight(False)
                update_device(iunit, 0, 'Off')

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Error to put off light for SPx'))
                ISCONNECTED = False
        elif Parameters['Mode3'] == 'MP1':
            if 1 < iunit < 6:
                try:
                    DEVICE.set_power(iunit - 1, False)
                    update_device(iunit, 0, 'Off')

                except (ValueError, Exception):
                    Domoticz.Error(traceback.format_exc())
                    Domoticz.Error(_('Error to put Off MP1 for plug : {}').format(str(iunit - 1)))
        else:
            try:
                update_device(iunit, 0, 'Off')

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Unit error update'))
                raise

    elif iunit == 1 and "RM" in Parameters["Mode3"]:
        if remote_send(command):
            update_device(iunit, 1, command)

        else:

            update_device(iunit, 1, _('undefined'))

    else:

        Domoticz.Error(_('Unknown command'))

    return True


# execution depend of Domoticz.Heartbeat(x) x in seconds
def onHeartbeat():
    global BYPASS, ISCONNECTED, STATE

    now = datetime.datetime.now()

    #
    # we check new plugin version on day 1
    #
    if now.day == 1 and now.hour == 0 and now.minute == 0:
        start_shell('remotePlugin')
    #
    # Bypass
    #
    if BYPASS is True:
        BYPASS = False

        return
    #
    # for RM2T/RM24T type we check temp every 2 minutes
    #
    if Parameters["Mode3"] == 'RM2T' or Parameters["Mode3"] == 'RM24T':
        if (now.minute % 2) == 0:
            BYPASS = True
            if ISCONNECTED:
                if check_temp():
                    update_device(4, 1, TEMP)
                    update_device(1, 1, 'On')

                else:

                    ISCONNECTED = False
                    update_device(1, 0, 'Off')

            else:

                if broadlink_connect():
                    update_device(1, 1, 'On')

                else:

                    update_device(1, 0, 'Off')
    #
    # for A1 we get sensor data every 30 seconds
    #
    elif Parameters["Mode3"] == 'A1':
        if INFOLEVEL > 0:
            Domoticz.Log(_("A1 called"))
        if (now.minute % 1) == 0:
            BYPASS = False
            if ISCONNECTED:
                if check_sensor():
                    update_device(1, 1, _('Get Data From Sensors'))

                else:

                    ISCONNECTED = False

            else:

                if broadlink_connect():
                    update_device(1, 1, 'On')

                else:

                    update_device(1, 0, 'Off')
    #
    # for SP3S we get energy/status data every 30 seconds
    #
    elif Parameters["Mode3"] == 'SP3S':
        if INFOLEVEL > 0:
            Domoticz.Log(_("SP3S called"))
        if (now.minute % 1) == 0:
            BYPASS = False
            if ISCONNECTED:
                if get_energy():
                    update_device(2, 0, str(ENERGY))
                    update_device(3, 0, str(ENERGY))

                else:

                    ISCONNECTED = False
                if check_power():
                    if STATE:
                        update_device(1, 1, 'On')

                    else:

                        update_device(1, 0, 'Off')

                else:

                    ISCONNECTED = False
                if check_light():
                    if STATE:
                        update_device(4, 1, 'On')

                    else:

                        update_device(4, 0, 'Off')

                else:

                    ISCONNECTED = False

            else:

                broadlink_connect()
    #
    # for MP1 we check status every 1 minute
    #
    elif Parameters["Mode3"] == 'MP1':
        if INFOLEVEL > 0:
            Domoticz.Log(_("MP1 called"))
        if (now.minute % 1) == 0:
            BYPASS = True
            if ISCONNECTED:
                if check_power_mp1():
                    if STATEMP1:
                        update_device(1, 1, 'On')
                        # AllPlugOn()

                    else:

                        update_device(1, 0, 'Off')
                        # AllPlugOff()

                else:

                    ISCONNECTED = False

            else:

                broadlink_connect()
    #
    # for SP1/2 we check status every 1 minute
    #
    elif Parameters["Mode3"] == 'SP1' or Parameters["Mode3"] == 'SP2':
        if INFOLEVEL > 0:
            Domoticz.Log(_("SP1/SP2 called"))
        if (now.minute % 1) == 0:
            BYPASS = True
            if ISCONNECTED:
                if check_power():
                    if STATE:
                        update_device(1, 1, 'On')

                    else:

                        update_device(1, 0, 'Off')

                else:

                    ISCONNECTED = False
                if check_light():
                    if STATE:
                        update_device(2, 1, 'On')

                    else:

                        update_device(2, 0, 'Off')

                else:

                    ISCONNECTED = False

            else:

                broadlink_connect()
    #
    # for RM2 we try to connect every 5 minutes
    #
    else:

        if now.minute % 5 == 0:

            if broadlink_connect():
                update_device(1, 1, 'On')

            else:
                
                update_device(1, 0, 'Off')

            BYPASS = True

    return True


#
def onMessage(iconnection, idata):
    global WEBROOT

    if INFOLEVEL > 1:
        Domoticz.Log(_("onMessage called for connection: {0}:{1}").format(iconnection.Address, iconnection.Port))

    urlok = ''
    url = ''
    todownload = False
    tochunck = False
    status = "200 OK"
    fname = ''

    if "Verb" in idata:
        #
        # we manage only GET / POST & OPTIONS verbs
        #
        str_verb = idata["Verb"]
        url = idata["URL"]
        #
        htmldata = \
            '''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8"/>
                <link rel="icon" href="data:,"/>
            </head>
            <body>
                <div style="text-align:center;">
                    <h3><p style="background : whitesmoke;">''' + _("Broadlink response OK!") + '''</p> :-)
                    </h3>
                </div>
                <script>
                    if ( window.history.replaceState ) {
                        window.history.replaceState( null, null, window.location.href );
                        }
                </script>
            </body>            
            </html>
            '''

        if str_verb == "GET":
            if INFOLEVEL > 1:
                Domoticz.Log(_("Request from : {}:{} to : {}").format(iconnection.Address, iconnection.Port, url))

            if idata['Headers']['Host'] == (Parameters['Address'] + ':' + Parameters['Mode5']) or \
                    Parameters['Mode5'] in idata['Headers']['Host']:

                if url == "/":
                    urlok = "base"

                elif "/web/" in url:
                    urlok = "web"
                    htmldata = readf((Parameters['HomeFolder'] + url), True)

                elif URLKEY in url:

                    if "showScan" in url:
                        urlok = "browser"
                        htmldata = readf((Parameters['HomeFolder'] + "log/" + "scan.txt"), False, False)

                    elif "showUsage" in url:
                        urlok = "browser"
                        htmldata = readf((Parameters['HomeFolder'] + "log/" + "usage.txt"), False, False)

                    elif "/info" in url:
                        urlok = "info"

                    elif "/creLanguage" in url:
                        urlok = 'creLanguage'

                    elif "/translateProgs" in url:
                        urlok = "translateProgs"

                    elif "/eControl" in url:
                        urlok = 'eControl'

                    elif "/import" in url:
                        urlok = 'import'

                    elif "/checkPlugin" in url:
                        urlok = 'checkPlugin'

                    elif "/test" in url:
                        urlok = "test"
                        iframe = \
                            '<iframe src="http://domoticz.com/"  width="100%" height="450" ' \
                            'frameborder="0" style="border:0" allowfullscreen></iframe>'
                        htmldata = htmldata + iframe

                    elif "/iniList" in url:
                        urlok = "iniList"
                        WEBROOT = False
                        htmldata = str(list_directory(Parameters['Mode2'], False))

                    elif "/list" in url:
                        urlok = "list"
                        WEBROOT = True
                        htmldata = str(list_directory(Parameters['HomeFolder'], False))

                    elif "/log" in url:
                        urlok = "log"
                        htmldata = domo_log()

                    elif "/createDevice" in url:
                        urlok = "createDevice"

                    elif "/delIni" in url:
                        urlok = 'delIni'

                    elif "/restartPlugin" in url:
                        urlok = "restartPlugin"
                        htmldata = \
                            ''' <div style="text-align:center;background : yellow;">
                                <h2><span style="background : green;">''' + _("Plugin restarted !") + '''</span>
                                <a onclick="document.location.reload(true);">
                                <button type="button" style="cursor: pointer;">''' + _("Refresh") + '''
                                </button>
                                </a>
                                </h2>
                                </div>
                            '''
                    elif "/updatePlugin" in url:
                        urlok = "updatePlugin"
                        htmldata = \
                            ''' <!DOCTYPE html>
                                <html>
                                <head>
                                <meta charset="UTF-8"/>
                                <link rel="icon" href="data:,"/>
                                </head>
                                <div style="text-align:center;">
                                    <h3>
                                        <p style="background: yellow;">''' + _(
                                "Broadlink plugin update finished ....") + \
                            '''</p>
                                        :-?
                                    </h3>
                                </div>
                                </html>
                                '''
                    elif "/backupPlugin" in url:
                        urlok = "backupPlugin"
                        htmldata = \
                            ''' <!DOCTYPE html>
                                <html>
                                <head>
                                    <meta charset="UTF-8"/>
                                    <link rel="icon" href="data:,"/>
                                </head>
                                <div style="text-align:center;">
                                    <h3>
                                        <p style="background: yellow;">''' + _("Backup finished.") + '''</p>
                                        :-?
                                    </h3>
                                </div>
                                </html>
                            '''
                    elif "/lngEditor" in url:
                        urlok = "lngEditor"
                        try:
                            parsed = urlparse.urlparse(url)
                            fname = parse_qs(parsed.query)['file'][0]
                            htmldata = html_editor(fname)

                        except (ValueError, Exception):
                            Domoticz.Error(traceback.format_exc())
                            Domoticz.Error(_('URL Error'))
                            htmldata = 'ERROR'

                    elif "/iniEditor" in url:
                        urlok = "iniEditor"
                        parsed = urlparse.urlparse(url)
                        fname = parse_qs(parsed.query)['file'][0]
                        htmldata = html_editor(fname)

                    elif "/manage" in url:
                        urlok = "manage"
                        htmldata = manage()

                    elif "/scanDevices" in url:
                        urlok = "scanDevices"
                        htmldata = countdown('showScan', 25)

                    elif "/usageDevices" in url:
                        urlok = "usageDevices"
                        htmldata = countdown('showUsage', 10)

                    elif "/sendCode" in url:
                        try:
                            parsed = urlparse.urlparse(url)
                            fname = Parameters['Mode2'] + (parse_qs(parsed.query)['ini'][0])
                            send_code(fname)

                        except (ValueError, Exception):
                            Domoticz.Error(traceback.format_exc())
                            Domoticz.Error(_('URL Error'))
                            htmldata = 'ERROR'

                    elif "/multiCode" in url:
                        urlok = "multiCode"
                        htmldata = multi_code()

                    else:

                        urlok = "unknown"
                        Domoticz.Error(
                            _("ERROR Unknown url from : {}:{} to : {}").format(iconnection.Address,
                                                                               iconnection.Port,
                                                                               url)
                                        )
                        htmldata = '''<!DOCTYPE html>
                            <html>
                            <head>
                                <meta charset="UTF-8"/>                        
                                <link rel="icon" href="data:,"/>
                            </head>
                            <div style="text-align:center;">
                                <h3><p style="background: yellow">''' + \
                                   _("Broadlink not know what to do!") + '''</p> :-( </h3>
                            </div>                        
                            </html> 
                            '''

                elif "Headers" in idata and "Referer" in idata["Headers"] and \
                        ((Parameters['Address'] + ':' + Parameters['Mode5']) in idata['Headers']['Referer'] or
                            Parameters['Mode5'] in idata['Headers']['Referer']):
                    # define root folder for browsing
                    if WEBROOT is True:
                        webdir = Parameters['HomeFolder']

                    else:

                        webdir = Parameters['Mode2']

                    if url.endswith((".txt", ".err", ".ini", ".cmd", ".sh")):
                        urlok = "browser"
                        htmldata = readf(webdir + urllib.parse.unquote(url[1:]), False)

                    elif url.endswith('/') and url.count("/") > 1:
                        urlok = "listdown"
                        htmldata = str(list_directory(webdir + url, True))

                    else:

                        urlok = "download"
                        todownload = True
                        htmldata = readf(webdir + urllib.parse.unquote(url[1:]), todownload)
                        fname = url[1:]

                else:

                    Domoticz.Error(
                        _("ERROR Unknown key from : {}:{} to : {}").format(iconnection.Address, iconnection.Port, url))

                    status = "401 Unauthorized"
                    htmldata = '''<!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8"/>                        
                            <link rel="icon" href="data:,"/>
                        </head>
                        <div style="text-align:center;">
                            <h3><p style="background: red">''' + _("Broadlink bad key!") + '''</p> :-( </h3>
                        </div>                        
                        </html> 
                        '''

                if todownload:
                    iconnection.Send({"Status": status,
                                      "Headers": {"Connection": "keep-alive",
                                                  "Accept": "Content-Type: octet/stream; charset=UTF-8",
                                                  "Accept-Encoding": "gzip, deflate",
                                                  "Content-Disposition": "attachment; filename=" + fname + ""},
                                      "Data": htmldata})
                elif tochunck:
                    iconnection.Send({"Status": "" + status + "",
                                      "Headers": {"Connection": "keep-alive",
                                                  "Accept": "Content-Type: text/html; charset=UTF-8",
                                                  "Accept-Encoding": "gzip, deflate",
                                                  "Access-Control-Allow-Origin": "http://" + Parameters['Address'] +
                                                                                 ":" +
                                                                                 Parameters['Port'] + "",
                                                  "Cache-Control": "no-cache, no-store, must-revalidate",
                                                  "Content-Type": "text/html; charset=UTF-8",
                                                  "Chunk": True,
                                                  "Pragma": "no-cache",
                                                  "Expires": "0"},
                                      "Data": "" + htmldata + ""})

                    iconnection.Send({"Chunk": True})

                elif urlok == 'web' and '.js' in url:

                    iconnection.Send({"Status": status,
                                      "Headers": {"Connection": "keep-alive",
                                                  "Accept": "Content-Type: octet/stream; charset=UTF-8",
                                                  "Accept-Encoding": "gzip, deflate",
                                                  "Cache-Control": "public, max-age = 604800, immutable",
                                                  "Content-Type": "application/javascript; charset=UTF-8"
                                                  },
                                      "Data": htmldata})

                elif urlok == 'web' and '.css' in url:

                    iconnection.Send({"Status": status,
                                      "Headers": {"Connection": "keep-alive",
                                                  "Accept": "Content-Type: octet/stream; charset=UTF-8",
                                                  "Accept-Encoding": "gzip, deflate",
                                                  "Cache-Control": "public, max-age = 604800, immutable",
                                                  "Content-Type": "text/css; charset=UTF-8"
                                                  },
                                      "Data": htmldata})

                elif urlok == 'base':

                    todownload = True
                    html_file = Parameters['StartupFolder'] + 'www/templates/Broadlink-' + Parameters['Mode3'] + '-' + \
                        str(Parameters["HardwareID"]) + '.html'
                    htmldata = readf(html_file, todownload)

                    if type(htmldata) is str:
                        message_length = len(htmldata.encode('utf8', 'replace'))

                    else:

                        message_length = len(htmldata)

                    iconnection.Send({"Status": status,
                                      "Headers": {"Connection": "keep-alive",
                                                  "Accept": "Content-Type: text/html; charset=UTF-8",
                                                  "Accept-Encoding": "gzip, deflate",
                                                  "Access-Control-Allow-Origin": "http://" + Parameters['Address'] +
                                                                                 ":" + Parameters['Port'] + "",
                                                  "Cache-Control": "no-cache, no-store, must-revalidate",
                                                  "Content-Type": "text/html; charset=UTF-8",
                                                  "Content-Length": "" + str(message_length) + "",
                                                  "Pragma": "no-cache",
                                                  "Expires": "0"},
                                      "Data": htmldata})

                else:

                    if type(htmldata) is str:
                        message_length = len(htmldata.encode('utf8', 'replace'))

                    else:

                        message_length = len(htmldata)

                    iconnection.Send({"Status": status,
                                      "Headers": {"Connection": "keep-alive",
                                                  "Accept": "Content-Type: text/html; charset=UTF-8",
                                                  "Accept-Encoding": "gzip, deflate",
                                                  "Access-Control-Allow-Origin": "http://" + Parameters['Address'] +
                                                                                 ":" + Parameters['Port'] + "",
                                                  "Cache-Control": "no-cache, no-store, must-revalidate",
                                                  "Content-Type": "text/html; charset=UTF-8",
                                                  "Content-Length": "" + str(message_length) + "",
                                                  "Pragma": "no-cache",
                                                  "Expires": "0"},
                                      "Data": htmldata})

            else:

                status = "501 Not Implemented "
                Domoticz.Error(
                    _("Not implemented Request from : {}:{} to : {}").format(iconnection.Address,
                                                                             iconnection.Port,
                                                                             url)
                                )
                htmldata = '''<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8"/>
                        <link rel="icon" href="data:,"/>
                    </head>
                <div style="text-align:center;">
                <h3><p style="background: red;">''' + _("Broadlink : not implemented !") + '''</p> :-?</h3>
                </div>
                </html>
                '''
                if type(htmldata) is str:
                    message_length = len(htmldata.encode('utf8', 'replace'))

                else:
                    message_length = len(htmldata)
                iconnection.Send({"Status": status,
                                  "Headers": {"Connection": "keep-alive",
                                              "Accept": "Content-Type: text/html; charset=UTF-8",
                                              "Accept-Encoding": "gzip, deflate",
                                              "Access-Control-Allow-Origin": "http://" + Parameters['Address'] +
                                                                             ":" + Parameters['Port'] + "",
                                              "Cache-Control": "no-cache, no-store, must-revalidate",
                                              "Content-Type": "text/html; charset=UTF-8",
                                              "Content-Length": "" + str(message_length) + "",
                                              "Pragma": "no-cache",
                                              "Expires": "0"},
                                  "Data": htmldata})

        elif str_verb == "POST":

            iconnection.Send({"Status": "200 OK",
                              "Headers": {"Connection": "keep-alive",
                                          "Accept": "Content-Type: text/html; charset=UTF-8",
                                          "Accept-Encoding": "gzip, deflate",
                                          "Access-Control-Allow-Origin": "*",
                                          "Cache-Control": "no-cache, no-store, must-revalidate",
                                          "Pragma": "no-cache",
                                          "Expires": "0"},
                              "Data": htmldata})

        elif str_verb == "OPTIONS":

            iconnection.Send({"Status": "200 OK",
                              "Headers": {"Connection": "keep-alive",
                                          "Allow": "OPTIONS, GET, POST",
                                          "Access-Control-Allow-Origin": "*",
                                          "Accept": "Content-Type: text/html; charset=UTF-8",
                                          "Accept-Encoding": "gzip, deflate",
                                          "Cache-Control": "no-cache, no-store, must-revalidate",
                                          "Pragma": "no-cache",
                                          "Expires": "0"},
                              "Data": htmldata})

        else:

            Domoticz.Log(str(idata))
            Domoticz.Error(_("Unknown verb in request: {}").format(str_verb))
            iconnection.Send({"Status": "421  Bad mapping ",
                              "Headers": {"Connection": "close",
                                          "Accept": "Content-Type: text/html; charset=UTF-8",
                                          "Accept-Encoding": "gzip, deflate",
                                          "Cache-Control": "no-cache, no-store, must-revalidate",
                                          "Pragma": "no-cache",
                                          "Expires": "0"},
                              "Data": "ERROR"})

    if urlok:
        # we have retrieved url from GET
        if INFOLEVEL > 1:
            Domoticz.Log(urlok)
        if urlok == 'scanDevices':
            start_shell('scan')
        elif urlok == 'usageDevices':
            start_shell('usage')
        elif urlok == 'backupPlugin':
            start_shell('backupPlugin')
        elif urlok == 'updatePlugin':
            start_shell('updatePlugin')
        elif urlok == "restartPlugin":
            restart_plugin()
        elif urlok == "createDevice":
            parsed = urlparse.urlparse(url)
            create_domdevice(iunit=parse_qs(parsed.query)['iunit'][0], icustom=parse_qs(parsed.query)['icustom'][0])
        elif urlok == "delIni":
            parsed = urlparse.urlparse(url)
            ifile = parse_qs(parsed.query)['file'][0]
            iplugunit = parse_qs(parsed.query)['plugunit'][0]
            delete_ini(ifile, iplugunit)
        elif urlok == "creLanguage":
            start_shell('crelang')
        elif urlok == "import":
            manage_ini_import(False)
        elif urlok == "eControl":
            create_ini_import()
        elif urlok == "checkPlugin":
            start_shell('remotePlugin')

    else:

        # work on received data - POST
        # Domoticz.Log(str(idata))
        if "URL" in idata and "POST" in idata["Verb"]:

            if URLKEY not in idata['URL']:
                if INFOLEVEL > 0:
                    Domoticz.Log(_('We bypass URL check'))

            else:

                if "/postupdDatas" in idata['URL']:
                    if ('updrepeat' in idata['URL']) or \
                            ('BROpronto' in idata['URL']) or \
                            ('Cremulti' in idata['URL']) or \
                            ('update_type' in idata['URL']):
                        Domoticz.Log(_('We process this url: {}').format(idata['URL']))

                    else:

                        uploadf(idata)
                        return

                elif ("/lngEditor" in idata['URL']) or ("/iniEditor" in idata['URL']):

                    uploadfile(idata)
                    return

                elif "/import" in idata['URL']:

                    manage_ini_import(False)
                    return

                elif "/sendCode" in idata['URL']:

                    parsed = urlparse.urlparse(idata['URL'])
                    fname = Parameters['Mode2'] + (parse_qs(parsed.query)['ini'][0])
                    send_code(fname)
                    return
        #
        # we process received data (json format mainly)
        #
        if "Data" in idata:
            receiveddata = str(idata['Data'])
            if INFOLEVEL > 1:
                Domoticz.Log("data:" + receiveddata)

            decodedata = idata['Data'].decode('utf-8', 'replace')

            if INFOLEVEL > 1:
                Domoticz.Log(decodedata)

            if process_data(decodedata):
                if INFOLEVEL > 1:
                    Domoticz.Log(_('data process OK'))

            else:

                Domoticz.Error(_('Error to process data'))

        else:

            Domoticz.Error(_('Nothing to do ...'))

    return


#
# executed when connect to remote device
#
def onConnect(iconnection, istatus, idescription):
    global HTTPCONNECTIONS, HTTPCLIENT

    if istatus == 0:
        if INFOLEVEL > 0:
            Domoticz.Log(_("Connected successfully to {}:{}").format(iconnection.Address, iconnection.Port))

    else:
        Domoticz.Log(_("Failed to connect ({}) to: {}:{} with error: {}").format(str(istatus),
                                                                                 iconnection.Address,
                                                                                 iconnection.Port,
                                                                                 idescription)
                     )
        Domoticz.Log(str(iconnection))

    if iconnection != HTTPCLIENT:
        HTTPCONNECTIONS[iconnection.Name] = iconnection
        HTTPCLIENT = iconnection

    return


#
# executed when closing connection from remote process
#
def onDisconnect(iconnection):
    if INFOLEVEL > 0:
        Domoticz.Log(_("onDisconnect called for connection '{}'").format(iconnection.Name))
        Domoticz.Log(_("Server Connections: "))
        for x in HTTPCONNECTIONS:
            Domoticz.Log("--> " + str(x) + "'.")

    if iconnection.Name in HTTPCONNECTIONS:
        del HTTPCONNECTIONS[iconnection.Name]

    return


#
# we update ini if changes has been done from Domoticz GUI/Json API and not plugin
#
def onDeviceModified(iunit):
    if INFOLEVEL > 0:
        Domoticz.Log(_('Device not modified by plugin'))

    if 'RM' in Parameters['Mode3']:

        mpath = str(Parameters["Mode2"]) + \
                str(Parameters["Key"]) + \
                "-" + \
                str(Parameters["HardwareID"]) + \
                "-" + \
                str('{:03d}'.format(iunit)) + \
                ".ini"

        if not os.path.exists(mpath):
            Domoticz.Error(_('ini file not found: {}').format(str(mpath)))
            return

        config = configparser.ConfigParser()
        config.read(mpath, encoding='utf8')

        try:
            if not (Devices[iunit].Name == config.get("DEFAULT", "customname")):
                config.set('DEFAULT', 'customname', Devices[iunit].Name)
                with open(mpath, 'w') as configfile:  # save
                    config.write(configfile)

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error to update the config file: customname'))

    return


# executed once when HW updated/removed
def onStop():
    Domoticz.Log("onStop called")

    html_file = Parameters['StartupFolder'] + "www/templates/Broadlink-" + Parameters['Mode3'] + "-" + \
        str(Parameters["HardwareID"]) + ".html"
    if os.path.exists(html_file):
        os.remove(html_file)

    for i in range(1, 4):
        if i in Devices:
            domunit = str(Devices[int(i)].ID)
            html_file = Parameters['StartupFolder'] + "www/templates/Broadlink-" + Parameters['Mode3'] + "-" + \
                str(Parameters["HardwareID"]) + '-' + domunit + ".html"
            if os.path.exists(html_file):
                os.remove(html_file)

    if HTTPCONNECTIONS:
        HTTPSERVERCONN.Disconnect()

    return


# Generic helper functions
def dump_config_to_log():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return


# Update Device into DB
def update_device(iunit, nvalue, svalue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if iunit in Devices:
        if iunit == 1 or (iunit == 4 and Parameters["Mode3"] == 'SP3S') or (
                (iunit == 2) and (Parameters["Mode3"] == 'SP1' or Parameters["Mode3"] == 'SP2')):
            if (Devices[iunit].nValue != nvalue) or (Devices[iunit].sValue != svalue):
                Devices[iunit].Update(nValue=nvalue, sValue=str(svalue))
                Domoticz.Log("Update " + str(nvalue) + ":'" + str(svalue) + "' (" + Devices[iunit].Name + ")")
        else:
            Devices[iunit].Update(nValue=nvalue, sValue=str(svalue))
            if INFOLEVEL > 1:
                Domoticz.Log("Update " + str(nvalue) + ":'" + str(svalue) + "' (" + Devices[iunit].Name + ")")
    return


#
# generate command to execute and update name in ini file if necessary
#
def gen_command(iunit):
    global LOADEDCOMMAND, SENDCOMMAND, NBUPDATE

    Domoticz.Log(_('Generate "ON" Command for learned code stored on unit/ini : {}').format(str(iunit)))
    remote = ''

    if iunit == 1:
        remote = 'remote/'

    mpath = str(Parameters["Mode2"]) + remote + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + \
        "-" + str('{:03d}'.format(iunit)) + ".ini"

    if not os.path.exists(mpath):
        Domoticz.Error(_('ini file not found: {}').format(str(mpath)))
        return

    config = configparser.ConfigParser()
    config.read(mpath, encoding='utf8')
    LOADEDCOMMAND = config.get("LearnedCode", str('{:03d}'.format(iunit)))
    if INFOLEVEL > 1:
        Domoticz.Log(" Code loaded : " + LOADEDCOMMAND)
    SENDCOMMAND = LOADEDCOMMAND

    if ISCONNECTED:
        if 'ini=' in SENDCOMMAND:
            start_shell('multi-code:' + mpath)

        else:

            send()

        if iunit in Devices:
            try:
                update_device(iunit, 1, 'On-' + str(NBUPDATE))
                NBUPDATE += 1

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_("Not able to update device : {}").format(str(iunit)))

            try:
                if not (Devices[iunit].Name == config.get("DEFAULT", "customname")):
                    config.set('DEFAULT', 'customname', Devices[iunit].Name)
                    with open(mpath, 'w', encoding='utf-8') as configfile:  # save
                        config.write(configfile)

            except (ValueError, Exception):
                Domoticz.Error(traceback.format_exc())
                Domoticz.Error(_('Error to update the config file : customname'))

    return


#
# retrieve adjust value for Temp device
#
def adjust_value(iunit):
    global ADJUSTVALUE

    params = {'type': 'devices', 'rid': Devices[iunit].ID}

    if exe_domoticz(params):
        if DOMDATA['status'] == 'OK':
            if 'result' in DOMDATA:
                ADJUSTVALUE = DOMDATA['result'][0]['AddjValue']

    return


#
# save learned/imported code into ini file
#
def save_ini():
    global UNIT, NUMBERDEV, CUSTOM

    NUMBERDEV += 1
    ipath = str(Parameters["Mode2"]) + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + "-" + \
        str('{:03d}'.format(NUMBERDEV)) + ".ini"

    if os.path.exists(ipath):
        Domoticz.Error(_('File exist : {}').format(ipath))

        return False

    else:

        try:
            create_config(ipath, str('{:03d}'.format(NUMBERDEV)), CUSTOM)
            Domoticz.Log('ini : {}'.format(NUMBERDEV))

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Not able to create : {}').format(ipath))

            return False

    return True


#
# create Domoticz device : push button
#
def create_domdevice(iunit, icustom):
    try:
        Domoticz.Device(Name=str(Parameters["HardwareID"]) + "-" + str(iunit) + " " + icustom,
                        Unit=int(iunit),
                        TypeName="Selector Switch",
                        Type=244,
                        Switchtype=9,
                        Subtype=73).Create()

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Not able to create device : {}').format(str(iunit)))

        return False

    return


#
# Delete ini file, optional Domoticz device
#
def delete_ini(ifile, iplugunit):
    try:
        if os.path.exists(ifile):
            os.remove(ifile)
        if int(iplugunit) in Devices:
            Devices[int(iplugunit)].Delete()
        Domoticz.Log(_('Ini file / Device deleted : {}').format(str(iplugunit)))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Error on delete_ini : {}').format(str(iplugunit)))

    return


#
# reset main Domoticz device values
#
def reset():
    global LEARNEDCOMMAND

    update_device(1, 1, _('reset IR/RF'))
    update_device(2, 0, 'Off')

    if DEVICE.check_frequency():
        update_device(3, 1, '20')

    else:

        update_device(3, 0, 'Off')

    DEVICE.cancel_sweep_frequency()
    LEARNEDCOMMAND = "None"
    if INFOLEVEL > 0:
        Domoticz.Log(_("Reset command executed"))

    return True


#
# send Hex command
#
def send():
    global SENDCOMMAND

    if not SENDCOMMAND:
        Domoticz.Error(_('Nothing to send'))

        return False

    SENDCOMMAND = bytes.fromhex(SENDCOMMAND)
    if INFOLEVEL > 0:
        Domoticz.Log(str(SENDCOMMAND))

    try:
        DEVICE.send_data(SENDCOMMAND)
        Domoticz.Log(_("Code sent...."))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_("Warning : Code sent ....Probably timeout"))

        return False

    return True


#
# Create a config file
#
def create_config(mpath, iunit, icustom):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'PluginKey': Parameters["Key"],
                         'PluginName': Parameters["Name"],
                         'PluginFolder': Parameters["HomeFolder"],
                         'HardwareID': Parameters["HardwareID"],
                         'Unit': iunit,
                         'CustomName': icustom
                         }

    config['Device'] = {'Host': Parameters["Mode4"],
                        'Mac': Parameters["Mode1"]}
    config['LearnedCode'] = {}
    unitecode = config['LearnedCode']
    unitecode[str(iunit)] = LEARNEDCOMMAND
    try:
        with open(mpath, 'w+', encoding='utf-8') as configfile:
            config.write(configfile)

    except IOError:
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Error to create the config file : {}').format(mpath))

        raise

    if INFOLEVEL > 0:
        Domoticz.Log(_("ini file created...{}").format(mpath))

    return


#
# connect to Broadlink
#
def broadlink_connect():
    global DEVICE, ISCONNECTED

    try:
        DEVICE = broadlink.gendevice(dev_type=read_type(),
                                     host=(Parameters["Mode4"], 80),
                                     mac=bytearray.fromhex(Parameters["Mode1"])
                                     )
        DEVICE.auth()
        ISCONNECTED = True
        Domoticz.Log(_("Connected to Broadlink device: {} {}").format(str(Parameters["Mode4"]), DEVICE.get_type()))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_("Error to connect to Broadlink device: {}").format(str(Parameters["Mode4"])))
        ISCONNECTED = False

        return False

    return True


#
# Retrieve device type from file
#
def read_type():
    devfile = Parameters['HomeFolder'] + "log/" + str(Parameters['HardwareID']) + Parameters['Mode3'] + ".txt"
    try:
        with open(devfile, 'r', encoding='utf-8') as f:
            value = f.read().split(' ')
            brotype = int(value[0], base=16)

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_("Error to retrieve type from this file : {}").format(devfile))
        brotype = 99999

    return brotype


#
# get temperature for RM2T
#
def check_temp():
    global TEMP

    try:
        TEMP = DEVICE.check_temperature()
        TEMP = round(TEMP + ADJUSTVALUE, 2)

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_("Error getting temperature data from Broadlink device....Timeout"))

        return False

    if TEMP > 60:
        return False

    return True


#
# import json files and transform to ini file and hex imported code for RM2/RM4 mini
#
def create_ini_import():
    global LEARNEDCOMMAND

    path = Parameters["Mode2"] + "import/"
    i = 0
    num_name = 0
    name = ''

    try:
        with open(path + "jsonSubIr", encoding='utf-8') as remote_name:
            data_remote = json.load(remote_name)

    except (ValueError, Exception):  # includes simplejson.decoder.JSONDecodeError
        Domoticz.Error(traceback.format_exc())

        return False

    try:
        with open(path + "jsonButton", encoding='utf-8') as button_name:
            data_button = json.load(button_name)

    except (ValueError, Exception):  # includes simplejson.decoder.JSONDecodeError
        Domoticz.Error(traceback.format_exc())

        return False

    try:
        with open(path + "jsonIrCode", encoding='utf-8') as code_name:
            data_code = json.load(code_name)

    except (ValueError, Exception):  # includes simplejson.decoder.JSONDecodeError
        Domoticz.Error(traceback.format_exc())

        return False

    rec_code = open(path + "simulate.txt", 'w+', encoding='utf-8')
    crlf = "\n"

    for i in range(0, len(data_code)):
        button = data_code[i]['buttonId']
        for j in range(0, len(data_button)):
            if data_button[j]['id'] == button:
                num_name = data_button[j]['subIRId']
                button_name = data_button[j]['name']
                for k in range(0, len(data_remote)):
                    if data_remote[k]['id'] == num_name:
                        name = data_remote[k]['name']
                        break

                    else:

                        name = "unknown"
                break

            else:

                button_name = "unknown"

        code = ''.join('%02x' % (i & 0xff) for i in data_code[i]['code'])
        result = "Numrec : " + str(i) + " " + \
                 "Button number: " + str(button) + " " + \
                 "Number name : " + str(num_name) + " " + \
                 "Name : " + name + " " + button_name + " " + \
                 "Code : " + str(code)
        icustom = name + " " + button_name
        path = Parameters["Mode2"] + "import/" + "IMP-" + str('{:03d}'.format(i)) + ".ini"

        LEARNEDCOMMAND = code
        create_config(path, str('{:03d}'.format(i)), icustom)
        rec_code.writelines(result + crlf)

        if INFOLEVEL > 0:
            Domoticz.Log(result)

    filelink = "file://" + Parameters["Mode2"] + "import/" + "simulate.txt"
    Domoticz.Log(_("Number of ini file to create : {}").format(str(i + 1)))
    Domoticz.Log(_("You need to select Import for that"))
    Domoticz.Log('Simulate.txt file has been created with all codes on it. Click <a target="_blank"  href="' +
                 filelink + '" style="color:blue">here</a> to see the path')

    return True


#
# if clear is True we will erase all files, if False we will create devices and erase ini files
#
def manage_ini_import(iclear):
    global CUSTOM, LEARNEDCOMMAND

    import glob
    import errno

    path = Parameters["Mode2"] + "import/*.ini"
    files = glob.glob(path)

    if not files:
        Domoticz.Log(_("No ini files found"))
        if iclear is False:
            return False

    else:

        for name in files:  # 'file' is a builtin type, 'name' is a less-ambiguous variable name.
            if iclear is False:
                try:
                    config = configparser.ConfigParser()
                    config.read(name, encoding='utf-8')
                    unitnumber = config.get("DEFAULT", "unit")
                    CUSTOM = config.get("DEFAULT", "customname")
                    LEARNEDCOMMAND = config.get("LearnedCode", str(unitnumber))
                    loop_ini()
                    LEARNEDCOMMAND = "None"

                except IOError as exc:
                    if exc.errno != errno.EISDIR:  # Do not fail if a directory is found, just ignore it.

                        raise  # Propagate other kinds of IOErro

            os.remove(name)
            if INFOLEVEL > 0:
                Domoticz.Log(_("Removing : {}").format(name))

    if iclear is True:
        path = Parameters["Mode2"] + "import/json*"
        files = glob.glob(path)
        if not files:
            Domoticz.Log(_("No json files found"))

            return False

        else:

            for name in files:
                os.remove(name)
                if INFOLEVEL > 0:
                    Domoticz.Log(_("Removing : {}").format(name))

    return True


#
# search for first number available
#
def loop_ini():
    if NUMBERDEV >= 254:
        Domoticz.Error(_('No more device available ...'))
        return False

    if not save_ini():
        loop_ini()

    return True


#
# search for remote command to send
#
def remote_send(command):
    if command in REMOTEKEY:
        k = REMOTEKEY.index(command)
        try:
            if REMOTETOSEND[k] != 0:
                gen_command(REMOTETOSEND[k])
                Domoticz.Log(_('Send .. : {} {} {}').format(str(k + 1), str(REMOTETOSEND[k]), command))

            else:

                Domoticz.Log(_('Bypass .. : {} {} {}').format(str(k + 1), str(REMOTETOSEND[k]), command))

        except IndexError:
            Domoticz.Error(_('Send error or command for remote controller not set into ini file: {}').format(command))
            Domoticz.Error(traceback.format_exc())

            return False

    else:

        Domoticz.Error(_('Command for remote not defined: {}').format(command))

        return False

    return True


#
# get config ini file for Kodi Remote
#
def get_remoteconfig():
    global REMOTECOMMAND

    name = str(Parameters["Mode2"]) + "remote/" + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + \
        "-" + str('{:03d}'.format(1)) + ".ini"

    if os.path.isfile(name):
        try:
            config = configparser.ConfigParser()
            config.read(name, encoding='utf-8')
            REMOTECOMMAND = config.get("Custom", "command")

        except IOError:
            Domoticz.Error(traceback.format_exc())
            raise  # Propagate other kinds of IOErro

        if INFOLEVEL > 1:
            Domoticz.Log(_("ini file read....{}").format(name))
            Domoticz.Log(_("Custom Commands: {}").format(REMOTECOMMAND))

    else:

        Domoticz.Error(_("No ini file : {}").format(name))
        Domoticz.Error(_("Custom Commands for Remote controller not managed"))

    return


#
# generate tuple for Kodi remote
#
def gen_remote():
    global REMOTEKEY, REMOTETOSEND

    from ast import literal_eval as make_tuple

    get_remoteconfig()
    if not REMOTECOMMAND.endswith(","):
        Domoticz.Error(_("Last character must be <,> into the remote controller file"))

    if REMOTECOMMAND:
        try:
            REMOTETOSEND = make_tuple(REMOTECOMMAND)

        except (ValueError, Exception):
            Domoticz.Error(_('Invalid number in ini file, string or leading zero'))

    REMOTEKEY = ("Home",
                 "Up",
                 "Info",
                 "Left",
                 "Select",
                 "Right",
                 "Back",
                 "Down",
                 "ContextMenu",
                 "ChannelUp",
                 "FullScreen",
                 "VolumeUp",
                 "Channels",
                 "ShowSubtitles",
                 "Mute",
                 "ChannelDown",
                 "Stop",
                 "VolumeDown",
                 "BigStepBack",
                 "Rewind",
                 "PlayPause",
                 "FastForward",
                 "BigStepForward"
                 )

    return


#
# retrieve sensors data and update devices  for type A1
#
def check_sensor():
    global TEMP

    # data
    try:
        data = DEVICE.check_sensors()

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_("Error getting sensor data from Broadlink device....Timeout"))

        return False

    if INFOLEVEL > 1:
        Domoticz.Log(str(data))

    # raw data
    try:
        data_raw = DEVICE.check_sensors_raw()

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_("Error getting sensor data raw from Broadlink device....Timeout"))

        return False

    if INFOLEVEL > 0:
        Domoticz.Log(str(data_raw))

    # temperature
    TEMP = round(data['temperature'] + ADJUSTVALUE, 2)

    update_device(2, 0, str(TEMP))

    # humidity
    hum = data['humidity']

    if hum < 40:
        hum_raw = "2"
    elif hum < 60:
        hum_raw = "0"
    elif hum < 70:
        hum_raw = "1"

    else:

        hum_raw = "3"

    update_device(3, int(hum), hum_raw)

    # air quality
    air = data['air_quality']
    air_raw = data_raw['air_quality']

    if air_raw == 0:
        air_raw = 400
    elif air_raw == 1:
        air_raw = 800
    elif air_raw == 2:
        air_raw = 1000
    elif air_raw == 3:
        air_raw = 1500

    else:

        air_raw = 2000

    update_device(4, int(air_raw), str(air))

    # noise
    # noi = data['noise']
    noi_raw = data_raw['noise']

    if noi_raw == 0:
        noi_raw = 0
    elif noi_raw == 1:
        noi_raw = 30
    elif noi_raw == 2:
        noi_raw = 60

    else:

        noi_raw = 100

    update_device(5, 0, int(noi_raw))

    # illumination
    # lux = data['light']
    lux_raw = data_raw['light']

    if lux_raw == 0:
        lux_raw = 10
    elif lux_raw == 1:
        lux_raw = 200
    elif lux_raw == 2:
        lux_raw = 400
    elif lux_raw == 3:
        lux_raw = 800

    else:

        lux_raw = 1600

    update_device(6, 0, int(lux_raw))

    return True


#
# SP1/2/3 devices
#
def check_power():
    global STATE

    try:
        STATE = DEVICE.check_power()
        if INFOLEVEL > 0:
            Domoticz.Log(_('State of the plug : {}').format(str(STATE)))

    except (ValueError, Exception):
        Domoticz.Error(_('Error to retrieve plug status'))
        if INFOLEVEL > 0:
            Domoticz.Error(traceback.format_exc())

        return False

    return True


def check_light():
    global STATE

    try:
        STATE = DEVICE.check_nightlight()
        if INFOLEVEL > 0:
            Domoticz.Log(_('State of the light : {}').format(str(STATE)))

    except (ValueError, Exception):
        Domoticz.Error(_('Error to retrieve light status'))
        if INFOLEVEL > 0:
            Domoticz.Error(traceback.format_exc())

        return False

    return True


#
# MP1 Device
#
def check_power_mp1():
    global STATEMP1

    STATEMP1 = {}

    try:
        STATEMP1 = DEVICE.check_power()
        if INFOLEVEL > 0:
            Domoticz.Log(_('Power state for device MP1 : {} ').format(str(STATEMP1)))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Error to check power state of MP1 device'))

        return False

    return True


#
# SP3s device (SP2)
#
def get_energy():
    global ENERGY

    try:
        ENERGY = DEVICE.get_energy()
        if INFOLEVEL > 0:
            Domoticz.Log(_('Energy for device SP3S: {}').format(str(ENERGY)))

    except (ValueError, Exception):
        Domoticz.Error(_('Error to get power energy from device SP3S'))
        if INFOLEVEL > 0:
            Domoticz.Error(traceback.format_exc())

        return False

    return True


#
# we put all switches of the MP1 device to Off
#
def all_plug_off():
    update_device(2, 0, 'Off')
    update_device(3, 0, 'Off')
    update_device(4, 0, 'Off')
    update_device(5, 0, 'Off')

    return


#
# we put all switches of the MP1 device to On
#
def all_plug_on():
    update_device(2, 1, 'On')
    update_device(3, 1, 'On')
    update_device(4, 1, 'On')
    update_device(5, 1, 'On')

    return


#
# we load lang dict: en;xx
#
def load_lang():
    global LANGDICT

    lang_file = Parameters['HomeFolder'] + 'lng/en_' + LANGTO + '.lng'
    try:
        with open(lang_file, 'r', encoding='utf-8') as fp:
            for line in fp:
                if not line.startswith('#--'):
                    key, val = line.split('|;|')
                    key = key.rstrip('\r\n')
                    if len(val) != 0:
                        val = val.rstrip('\r\n')
                    LANGDICT[key] = val.rstrip('\r\n')

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Lang file not exist or problem to read data from : {}').format(lang_file))

        return False

    Domoticz.Log(_('lang file : {}').format(lang_file))

    return True


#
# Command to initialize the subprocess
#
def start_shell(*args):
    #
    # what to do ?
    todo = ''
    if args:
        todo = args[0]
    else:
        if INFOLEVEL > 1:
            Domoticz.Log(_('argument is missing'))

            return False

    cmdargs = '"' + \
              str(Parameters['Address']) + ';' + \
              str(Parameters['Port']) + ';' + \
              '' + Parameters['Mode1'] + '' + ';' + \
              '' + Parameters['Mode2'] + '' + ';' + \
              '' + Parameters['Mode3'] + '' + ';' + \
              '' + Parameters['Mode4'] + '' + ';' + \
              '' + Parameters['Mode5'] + '' + ';' + \
              '' + Parameters['Mode6'] + '' + ';' + \
              str(Parameters['HardwareID']) + ';' + \
              '' + Parameters['HomeFolder'] + '' + ';' + \
              str(INFOLEVEL) + ';' + \
              str(LANGTO) + ';' + \
              str(todo) + \
              '"'

    # now we can create the full command
    command = '"' + \
              Parameters['HomeFolder'] + \
              CMD + \
              '" ' + \
              '"' + Parameters['HomeFolder'] + 'Dombroadlink.py" ' + cmdargs + ' no '

    if INFOLEVEL > 1:
        Domoticz.Log(_('command to execute : {}').format(command))

    # launch the cmd
    try:
        subprocess.check_call(command, shell=True, timeout=1)

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('ERROR to start subprocess'))

        return False

    return True


#
# check if port is already opened or not
#
def is_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)

        return True

    except (ValueError, Exception):

        return False


#
# execute json request to Domoticz
#
def exe_domoticz(params):
    global DOMDATA

    try:
        params = urllib.parse.urlencode(params)
        ihtml = urllib.request.urlopen(
            'http://' + '127.0.0.1' + ':' + str(Parameters['Port']) + '/json.htm?' + params, timeout=2)
        response = ihtml.read()
        encoding = ihtml.info().get_content_charset('utf-8')
        DOMDATA = json.loads(response.decode(encoding))
        if INFOLEVEL > 1:
            Domoticz.Log(_('Request from domoticz to : {} with encoding : {}').format(str(params), str(encoding)))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Error sending command to Domoticz : {}').format(str(params)))

        return False

    return True


#
# Manage file upload
#
def uploadf(fdata):
    fn = ''
    mtype = fdata['Headers']['Content-Type']
    mtps = fdata['Data']

    decoder = MultipartDecoder(mtps, mtype)

    for items in decoder.parts:
        contentdisp = (items.headers[b'Content-Disposition']).decode('utf-8')
        contenttype = (items.headers[b'Content-Type']).decode('utf-8')

        if INFOLEVEL > 0:
            Domoticz.Log('Content-Disposition : ' + contentdisp)
            Domoticz.Log('Content-Type        : ' + contenttype)

        findkey = re.search("filename=(.)*", contentdisp)
        if findkey:
            fn = re.sub('"', '', (re.sub('filename=', '', findkey.group())))

        if fn and DISPLAYPATH:
            fn = DISPLAYPATH + fn
            if INFOLEVEL > 0:
                Domoticz.Log('File to create : ' + fn)

            if 'Text/Plain' not in contenttype:
                try:
                    with open(fn, 'w+b') as fp:
                        fp.write(items.content)

                    Domoticz.Log(_('File {} uploaded.').format(fn + ' --binary--'))

                except (ValueError, Exception):
                    Domoticz.Log(traceback.format_exc())
                    Domoticz.Error(_('Error to create file : {}').format(fn))

            else:

                try:
                    with open(fn, 'w', encoding='utf-8') as fp:
                        fp.write(items.text)
                    Domoticz.Log(_('File {} uploaded.').format(fn + ' <text>'))

                except (ValueError, Exception):
                    Domoticz.Log(traceback.format_exc())
                    Domoticz.Error(_('Error to create file : {}').format(fn))

        else:

            Domoticz.Error(_('Error to find file name from: {} or not valid path: {}').format(contentdisp, DISPLAYPATH))

    return


#
# Manage file update from Editor
#
def uploadfile(mata):
    fn = ''
    itype = mata['Headers']['Content-Type']
    mtps = mata['Data']

    decoder = MultipartDecoder(mtps, itype)

    for items in decoder.parts:
        contentdisp = (items.headers[b'Content-Disposition']).decode('utf-8')
        contenttype = 'form'

        if INFOLEVEL > 0:
            Domoticz.Log('Content-Disposition : ' + contentdisp)
            Domoticz.Log('Content-Type        : ' + contenttype)

        findkey = re.search("name=(.)*", contentdisp)

        if findkey:
            fn = re.sub('"', '', (re.sub('name=', '', findkey.group())))

        if fn:
            # fn = Parameters['HomeFolder'] + fn
            if INFOLEVEL > 0:
                Domoticz.Log('File to create : ' + fn)

            if 'Text/Plain' not in contenttype:
                try:
                    with open(fn, 'w+b') as fp:
                        fp.write(items.content)
                    Domoticz.Log(_('File {} uploaded.').format(fn + ' --binary--'))

                except (ValueError, Exception):
                    Domoticz.Log(traceback.format_exc())
                    Domoticz.Error(_('Error to create file : {}').format(fn))

            else:

                try:
                    with open(fn, 'w', encoding='utf-8') as fp:
                        fp.write(items.text)
                    Domoticz.Log(_('File {} uploaded.').format(fn + ' <text>'))

                except (ValueError, Exception):
                    Domoticz.Log(traceback.format_exc())
                    Domoticz.Error(_('Error to create file : {}').format(fn))

        else:

            Domoticz.Error(_('Error to find file name from : {}').format(contentdisp))

    return


#
# request to send code stored in ini file
#
def send_code(ifname):
    global SENDCOMMAND

    Domoticz.Log(_('we send code from : {}').format(ifname))

    if os.path.exists(ifname):
        try:
            config = configparser.ConfigParser()
            config.read(ifname, encoding='utf8')
            unitn = config.get("DEFAULT", "unit")
            iloadedcommand = config.get("LearnedCode", str(unitn))
            if INFOLEVEL > 1:
                Domoticz.Log(_("Code loaded : {}").format(iloadedcommand))
            SENDCOMMAND = iloadedcommand

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Not able to load command from {}').format(ifname))

        if ISCONNECTED:
            if 'ini=' in SENDCOMMAND:
                start_shell('multi-code:' + ifname)

            else:

                send()
        else:

            Domoticz.Error(_('Not able to send command : Not connected'))
    else:

        Domoticz.Error(_('Not able to find file {}').format(ifname))

    return


#
# main loop to know what to do from received data
#
def process_data(recdata):
    global LEARNEDCOMMAND, CUSTOM, NEWPLUGIN

    if 'fpronto=' in recdata:

        CUSTOM = 'Pronto HEX import'

        try:
            code = (urllib.parse.unquote_plus(recdata[8:])).strip().replace(" ", "")
            if INFOLEVEL > 1:
                Domoticz.Log("pronto code:" + str(code))
            pronto = bytearray.fromhex(code)
            pulses = pronto2lirc(pronto)
            packet = lirc2broadlink(pulses)
            LEARNEDCOMMAND = (codecs.encode(packet, 'hex_codec')).decode('utf-8')
            loop_ini()
            LEARNEDCOMMAND = "None"

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error on fpronto from Received Data: {}').format(str(recdata)))

            return False

    elif 'updrepeat=' in recdata:

        try:
            repeat = int(recdata[10:recdata.find('&')])
            fname = urllib.parse.unquote_plus(recdata[recdata.find('&') + 9:])
            config = configparser.ConfigParser()
            config.read(fname, encoding='utf-8')
            unitnumber = config.get("DEFAULT", "unit")
            command = config.get("LearnedCode", str(unitnumber))
            if 'ini=' in command:
                Domoticz.Error(_('Error to update the config file : multi-code'))

            else:

                newcommand = command[0:2] + '{:02x}'.format(repeat) + command[4:]
                config.set('LearnedCode', unitnumber, newcommand)
                with open(fname, 'w', encoding='utf-8') as configfile:  # save
                    config.write(configfile)

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error to update the config file : repeat'))

            return False

    elif 'ini=' in recdata:

        CUSTOM = 'Multi-Code'

        try:
            if INFOLEVEL > 1:
                Domoticz.Log("Multi-code : " + recdata)
            LEARNEDCOMMAND = recdata
            loop_ini()
            LEARNEDCOMMAND = "None"

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error on Multi-code from Received Data: {}').format(str(recdata)))

            return False

    elif 'devtype=' in recdata:

        Domoticz.Log("Update_device : " + str(hex(int(recdata[8:]))))

        devfile = Parameters['HomeFolder'] + "log/" + str(Parameters['HardwareID']) + Parameters['Mode3'] + ".txt"
        try:
            dev = str(hex(int(recdata[8:]))) + " " + Parameters["Mode4"] + " " + Parameters["Mode1"]
            with open(devfile, 'w', encoding='utf-8') as fp:
                fp.write(dev)
            Domoticz.Log(_('Command line file created: {}').format(devfile))

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error to create device file : {}').format(devfile))

    else:

        try:
            recdata_json = json.loads(recdata)

        except (ValueError, Exception):
            Domoticz.Log(traceback.format_exc())
            Domoticz.Error(_('Error on json from Received Data: {}').format(str(recdata)))

            return False

        if INFOLEVEL > 1:
            Domoticz.Log(_('processing data : {}').format(recdata))

        if "status" in recdata_json:
            idata = recdata_json['status']
            if idata['step'] == 'learnir':
                update_device(1, 1, idata['msg'])
                if idata['code'] == '0':
                    update_device(2, 1, '20')
                else:
                    update_device(2, 0, 'Off')
            elif idata['step'] == 'sweep':
                update_device(1, 1, idata['msg'])
                if idata['code'] == '0':
                    update_device(3, 1, '20')
                else:
                    update_device(3, 0, 'Off')
            elif idata['step'] == 'learnrf':
                update_device(1, 1, idata['msg'])
                if idata['code'] == '0':
                    update_device(3, 1, '30')
                else:
                    update_device(3, 0, 'Off')
            elif idata['step'] == 'remotePlugin':
                if idata['code'] == '99':
                    Domoticz.Log(_("New version available"))
                    NEWPLUGIN = "yes"
            elif 'ERR :' in idata['step']:
                Domoticz.Error(idata['step'] + "--" + idata['msg'] + "--" + idata['code'])

            else:

                Domoticz.Log(idata['step'] + "--" + idata['msg'] + "--" + idata['code'])

        elif "end" in recdata_json:
            idata = recdata_json['end']
            if 'RM' in Parameters['Mode3'] or Parameters['Mode3'] == 'A1':
                update_device(1, 1, idata['msg'])
                if ISCONNECTED:
                    update_device(1, 1, 'On')

            else:

                Domoticz.Log(idata['msg'])

        elif "learned_command" in recdata_json:
            idata = recdata_json['learned_command']
            LEARNEDCOMMAND = idata['data']

        else:

            Domoticz.Error(_('we do not know what to do of received data'))

            return False

    return True


#
# retrieve plugin version
#
def plugin_ver(fn):
    try:
        with open(fn, 'r', encoding='utf-8') as v:
            data = v.read()
            findkey = re.search('version="(.)*?"', data)
            ver = findkey.group()

    except (ValueError, Exception):
        Domoticz.Log(traceback.format_exc())
        Domoticz.Error(_('Error to retrieve plugin version from : {}').format(fn))
        ver = "**ERROR**"

    return ver


#
# set color depend of device state
#
def colorstate(iunit):
    try:
        if Devices[iunit].sValue == 'On':
            color = '#5e8f5e'

        else:

            color = 'red'

    except (ValueError, Exception):

        color = 'orange'

    return color


#
# load base64 image into variable
#
def load_img64(name):
    img = ''
    imgfile = Parameters['HomeFolder'] + 'web/img/' + name

    try:
        with open(imgfile, 'r', encoding='utf-8') as fp:
            img = fp.read()

    except (ValueError, Exception):
        Domoticz.Log(traceback.format_exc())
        Domoticz.Error(_('Error to read image file :{}').format(name))

    return img


#
# restart plugin after param update or manual request
#
def restart_plugin():
    hwinfo = {
        "type": "command",
        "param": "updatehardware",
        "htype": "94",
        "idx": Parameters["HardwareID"],
        "name": Parameters["Name"],
        "username": "",
        "password": "",
        "address": Parameters["Address"],
        "port": Parameters["Port"],
        "serialport": Parameters["SerialPort"],
        "Mode1": Parameters["Mode1"],
        "Mode2": Parameters["Mode2"],
        "Mode3": Parameters["Mode3"],
        "Mode4": Parameters["Mode4"],
        "Mode5": Parameters["Mode5"],
        "Mode6": Parameters["Mode6"],
        "extra": Parameters["Key"],
        "enabled": "true",
        "datatimeout": "0"
    }

    # we will kill connection so trouble should happen:
    # this is why we pass to avoid error message
    try:
        params = urllib.parse.urlencode(hwinfo)
        urllib.request.urlopen(
            'http://' + str(Parameters['Address']) + ':' + str(Parameters['Port']) + '/json.htm?' + params, timeout=2)

    except (ValueError, Exception):
        pass

    return True


#
# Convert from pronto HEX to broadlink code
# From https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f
#

def pronto2lirc(pronto):
    codes = [int(binascii.hexlify(pronto[i:i + 2]), 16) for i in range(0, len(pronto), 2)]
    if codes[0]:
        raise ValueError('Pronto code should start with 0000')
    if len(codes) != 4 + 2 * (codes[2] + codes[3]):
        raise ValueError('Number of pulse widths does not match the preamble')
    frequency = 1 / (codes[1] * 0.241246)
    return [int(round(code / frequency)) for code in codes[4:]]


def lirc2broadlink(pulses):
    array = bytearray()
    for pulse in pulses:
        pulse = pulse * 269 / 8192  # 32.84ms units
        if pulse < 256:
            array += bytearray(struct.pack('>B', int(pulse)))  # big endian (1-byte)

        else:

            array += bytearray([0x00])  # indicate next number is 2-bytes
            array += bytearray(struct.pack('>H', int(pulse)))  # big endian (2-bytes)

    packet = bytearray([0x26, 0x00])  # 0x26 = IR, 0x00 = no repeats
    packet += bytearray(struct.pack('<H', len(array)))  # little endian byte count
    packet += array
    packet += bytearray([0x0d, 0x05])  # IR terminator

    # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
    remainder = (len(packet) + 4) % 16  # rm.send_data() adds 4-byte header (02 00 00 00)
    if remainder:
        packet += bytearray(16 - remainder)

    return packet


#
# check if new version exist
#
def checkver():
    global NEWPLUGIN

    fn = Parameters['HomeFolder'] + 'tst-plugin'
    if os.path.exists(fn):
        remotever = plugin_ver(fn)
        fn = Parameters['HomeFolder'] + 'plugin.py'
        actualver = plugin_ver(fn)
        if remotever != actualver:
            NEWPLUGIN = 'yes'
        else:
            NEWPLUGIN = 'no'

    return


#
# Admin page html
# custom page need to be allowed in Domoticz if want to see it on Domoticz menu
#
def htmladmin(name, iframe):
    fn = Parameters['HomeFolder'] + 'plugin.py'
    pluginver = plugin_ver(fn)
    verinfo = ''
    mpath = Parameters['HomeFolder'] + 'lng/en_' + LANGTO + '.lng'
    #
    msgconfirmd = _("Are you sure ? you need to restart Plugin after ...")
    msgconfirmp = _("Are you sure you want restart Plugin ?")
    msgconfirmu = _("Are you sure you want update Plugin ?")
    msgconfirmb = _("Are you sure you want backup Plugin data ?")

    url_post = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/postupdDatas?key=' + URLKEY
    url_lang = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/creLanguage?key=' + URLKEY
    url_manage = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/manage?key=' + URLKEY
    url_ini = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/iniList?key=' + URLKEY
    url_restart = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/restartPlugin?key=' + URLKEY
    url_dir = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/list?key=' + URLKEY
    url_log = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/log?key=' + URLKEY
    url_upd = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/updatePlugin?key=' + URLKEY
    url_edit = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/lngEditor?key=' + URLKEY
    url_bkp = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/backupPlugin?key=' + URLKEY
    url_chk = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/checkPlugin?key=' + URLKEY
    url_trans = ''   # 'https://mymemory.translated.net/'

    hwidx = Parameters['HardwareID']
    if 1 in Devices:
        domunit = str(Devices[int(1)].ID)

    else:

        domunit = '**unknown**'

    devtype = '***'
    manu = '***'

    try:
        if hasattr(DEVICE, 'devtype'):
            devtype = str(hex(DEVICE.devtype))

        if hasattr(DEVICE, 'manufacturer'):
            manu = str(DEVICE.manufacturer)

    except (ValueError, Exception):
        if INFOLEVEL > 0:
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error retrieve data from device : {}').format(domunit))
        pass

    nbrdev = len(Devices)
    if Parameters['Mode3'] == 'RM2M' or Parameters['Mode3'] == 'RM24M':
        img64 = load_img64('RM2M.txt')
    elif 'RM' in Parameters['Mode3']:
        img64 = load_img64('RM2.txt')
    elif 'SP' in Parameters['Mode3']:
        img64 = load_img64('SP.txt')
    elif Parameters['Mode3'] == 'MP1':
        img64 = load_img64('MP1.txt')
    elif Parameters['Mode3'] == 'A1':
        img64 = load_img64('A1.txt')

    else:

        img64 = load_img64('UNK.txt')

    # page creation
    dataadmin = '''<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta charset="UTF-8"/>
        <meta http-equiv="expires" content="0"/>
        <title>Broadlink WebAdmin</title>
        <link rel="icon" href="data:,"/>
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + '''/web/css/button.css" 
            rel = "stylesheet">        
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
                '''/css/ui-darkness/jquery-ui.min.css" rel = "stylesheet">

'''
    if autoresize:
        dataadmin += '''
        <script type="text/javascript" src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                     '''/web/js/iframeResizer.js"></script>    
'''

    dataadmin += '''
       
        <script type="text/javascript">
        
           if (typeof jQuery == 'undefined') {
            var script = document.createElement('script');
            script.type = "text/javascript";
            script.src = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
                 '''/js/jquery-3.4.1.min.js";
            document.getElementsByTagName('head')[0].appendChild(script);
            }   
           if (typeof jQuery == 'undefined') {
            var script = document.createElement('script');
            script.type = "text/javascript";
            script.src = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
                 '''/js/jquery-ui.min.js";
            document.getElementsByTagName('head')[0].appendChild(script);
            }
               
        </script>

        <style>
        * {
          box-sizing: border-box;
        }

        #ezProgress {
            width: 100%;
            background-color: #ddd;
        }

        #ezBar {
            width: 1%;
            height: 10px;
            background-color: #4CAF50;
            text-align: center;
            line-height: 10px;
            color: white;
        }

        /* Create three equal columns that floats next to each other */
        .column {
          float: left;
          width: 33.33%;
          padding: 2px;
          height: 150px;
          color: black;
        }

        /* Clear floats after the columns */
        .row:after {
          content: "";
          display: table;
          clear: both;
        }

        /* Responsive layout - makes the three columns stack on top of each other instead of next to each other */
        @media screen and (max-width: 1024px) {
          .column {
            width: 100%;
            }
          .content-mobile {
            display: none;
            }
        }

        table, th, td {
            border: 1px solid white;
            border-collapse: collapse;
        }
        th, td {
            padding: 1px;
        }
        
        #scroll_to_top {
          position: fixed;
          width: 35px;
          height: 35px;
          bottom: 50px;
          right: 50px;
          display: none;
        }

        
        </style>
    </head>
    <body>
        <script type="text/javascript">

        function ezid(el) {
          return document.getElementById(el);
        }
    
        function uploadFile() {
          var file = ezid("ezfile").files[0];
          // alert(file.name+" | "+file.size+" | "+file.type);
          if (file == undefined) {
            alert("''' + _("File name is required") + '''");
            return false;
            }
          var formdata = new FormData();
          formdata.append("ezfile", file);
          var ajax = new XMLHttpRequest();
          ajax.upload.addEventListener("progress", progressHandler, false);
          ajax.addEventListener("load", completeHandler, false);
          ajax.addEventListener("error", errorHandler, false);
          ajax.addEventListener("abort", abortHandler, false);
          ezid("ezStatus").innerHTML = "";
          ezid("ezadminframe").innerHTML = ezid("ezadminframe").innerHTML 
          ajax.open("POST", "''' + url_post + '''");
          ajax.send(formdata);
        }
    
        function progressHandler(event) { 
          ezid("ezUpl").innerHTML = "''' + _("Uploaded ") + ''': " + event.loaded + " ''' + _(" bytes of ") + \
                 ''': " + event.total;
          ezid("ezStatus").innerHTML = "''' + _("Work in progress") + '''";
          var percent = (event.loaded / event.total) * 100;
          ezid("ezBar").style.width = Math.round(percent) + '%'; 
          ezid("ezBar").innerHTML = Math.round(percent) * 1  + '%';
          ezid("ezStatus").innerHTML = Math.round(percent) + "''' + _("% uploaded... please wait") + '''";
        }
    
        function completeHandler(event) {
          ezid("ezStatus").innerHTML = event.target.responseText;
        }
    
        function errorHandler(event) {
          ezid("ezStatus").innerHTML = "''' + _("Upload Failed") + '''";
        }
    
        function abortHandler(event) {
          ezid("ezStatus").innerHTML = "''' + _("Upload Aborted") + '''";
        }
    
        function resetBar() {
          ezid("ezBar").style.width = '1%'; 
          ezid("ezBar").innerHTML = '0%';
          ezid("ezStatus").innerHTML = "";
          ezid("ezUpl").innerHTML = "";
        }
    
        function updatePlugin() {
          if (confirm(\'''' + msgconfirmu + '''\')){
              var ajax = new XMLHttpRequest();
              ajax.upload.addEventListener("progress", progressRestart, false);
              ajax.addEventListener("load", completeUpdate, false);
              ajax.addEventListener("error", errorRestart, false);
              ajax.addEventListener("abort", abortRestart, false);
              ezid("ezStatus").innerHTML = "''' + _("Work in progress") + '''";
              ezid("ezadminframe").innerHTML = ezid("ezadminframe").innerHTML 
              ajax.open("GET", "''' + url_upd + '''",true);
              ajax.send(null);
            }
        }
    
        function backupPlugin() {
          if (confirm(\'''' + msgconfirmb + '''\')){
              var ajax = new XMLHttpRequest();
              ajax.upload.addEventListener("progress", progressRestart, false);
              ajax.addEventListener("load", completeBackup, false);
              ajax.addEventListener("error", errorRestart, false);
              ajax.addEventListener("abort", abortRestart, false);
              ezid("ezStatus").innerHTML = "''' + _("Work in progress") + '''";
              ezid("ezadminframe").innerHTML = ezid("ezadminframe").innerHTML 
              ajax.open("GET", "''' + url_bkp + '''",true);
              ajax.send(null);
            }
        }
    
        function completeBackup(event) {
          ezid("ezStatus").innerHTML = event.target.responseText;
        }
    
        function completeUpdate(event) {
          ezid("ezStatus").innerHTML = event.target.responseText;
          alert("''' + _("Wait for few seconds before restarting") + '''");
          restartPlugin();
        }
    
        function restartPlugin() {
          if (confirm(\'''' + msgconfirmp + '''\')){
              var ajax = new XMLHttpRequest();
              ajax.upload.addEventListener("progress", progressRestart, false);
              ajax.addEventListener("load", completeRestart, false);
              ajax.addEventListener("error", errorRestart, false);
              ajax.addEventListener("abort", abortRestart, false);
              ezid("ezStatus").innerHTML = "''' + _("Work in progress") + '''";
              ezid("ezadminframe").innerHTML = ezid("ezadminframe").innerHTML 
              ajax.open("GET", "''' + url_restart + '''",true);
              ajax.send(null);
            }
        }
    
        function progressRestart(event) {
          ezid("ezStatus").innerHTML = "''' + _("Work in progress") + '''";
        }
    
        function completeRestart(event) {
          ezid("ezStatus").innerHTML = event.target.responseText;
        }
    
        function errorRestart(event) {
          ezid("ezStatus").innerHTML = "''' + _("Restart Failed") + '''";
        }
    
        function abortRestart(event) {
          ezid("ezStatus").innerHTML = "''' + _("Restart Aborted") + '''";
        }

        function myload() {
            $(document).ready(function(){
                $(document).tooltip();
                var newver = \'''' + NEWPLUGIN + '''\';
                if ( newver === 'yes' ) { ezid("ezStatus").innerHTML = "''' + _("New version available") + '''"; };
        
                $(".popup").click(function (event) {
                    event.preventDefault();
                    var page = $(this).attr("href");
                    var title = $(this).text();
                    var windowsize = $(window).width();
                    if (windowsize > 1020) {
                        //if the window is greater than 1020px wide then open dialog..
                        //alert('> 1024');
                        $('<div></div>')
                        .html('<iframe style="border: 0px; " src="' + page + '" width="100%" height="100%"></iframe>')
                        .dialog({
                            autoOpen: true,
                            modal: false,
                            height: 600,
                            width: 900,
                            title: title,
                            show: 'slideDown',
                            position : { my: "center", at: "center", of: window }
                                });
                        } else {
                        //alert('< 1024');
                        window.open(this.href, this.target);
                    }
                });
                $(".devpopup").click(function (event) {
                    event.preventDefault();
                    var page = $(this).attr("href");
                    var title = $(this).text();
                    var windowsize = $(window).width();
                    seconds = 360;
                    if (windowsize > 600) {
                        //if the window is greater than 1020px wide then open dialog..
                        //alert('> 1024');
                        $('<div></div>')
                        .html('<iframe style="border: 0px; " src="' + page + '" width="100%" height="100%"></iframe>')
                        .dialog({
                            autoOpen: true,
                            modal: false,
                            height: 400,
                            width: 600,
                            title: title,
                            show: 'slideDown',
                            position : { my: "top", at: "top", of: event },
                            close: function( event, ui ) {window.location.reload();}                          
                                });
                                
                        } else {
                        //alert('< 1024');
                        window.open(this.href, this.target);
                    }
                });
                
                
                function scroll_to_top(div) {
                    $(div).click(function() {
                        $('html,body').animate({scrollTop: 0}, 'slow');
                    });
                    $(window).scroll(function(){
                        if($(window).scrollTop()<200){
                            $(div).fadeOut();
                        } else{
                            $(div).fadeIn();
                        }
                    });
                }
                
                scroll_to_top("#scroll_to_top");                    
        
            });
        }
        

        if (typeof jQuery != 'undefined') {
        
            myload();
                        
        } else {

        window.onload=function() {
        
            myload();
            
                }
        }


        </script>
        
        <div class="row">
            <div id="content-mobile-1" class="column content-mobile" 
                style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                background-color:#aaa; text-align: center;">
                <img src="''' + str(img64) + '''" alt="Broadlink" height="100" width="100" onclick="restartPlugin()" 
                style="cursor: pointer;" title="''' + _("Restart") + '''">
                <h1 style="color: ''' + colorstate(1) + ''';font-size: 22px;">
                     ''' + manu + ''' : ''' + Parameters['Mode3'] + ' --- ' + devtype + '''
                    <a onclick="$('#update_type').dialog({height: 200,width: 400,modal: false, show:'fold'});">
                    <span style="cursor: pointer;" title="''' + _('Overwrite default device type') + '''">&#8617;</span>
                    </a>
                </h1>            
            </div>
            <div class="column" style="border-radius: 10px;box-shadow: 5px 5px 10px rgba(0,0,0,0.5);
            background-color:#bbb;text-align:center;">
                <h1 style="color: ''' + colorstate(1) + ''';">''' + name + '''</h1>
                <form id="upload_form" enctype="multipart/form-data" method="post" target="adminframe">
                    <input type="file" name="ezfile" id="ezfile" required autocomplete="off" onchange="resetBar();">
                    <a onclick="uploadFile();">
                        <span style="cursor: pointer;" title="''' + _("Upload file to plugin folder") + '''">
                            &#9989;
                        </span>
                    </a>
                    <div id="ezProgress" style="height:10px;">
                        <div id="ezBar">0%</div>
                        <span id="ezStatus" style="background-color:gray;height:10px;">status</span>
                    </div>
                </form>
            </div>
            <div id="content-mobile-2" class="column content-mobile" 
                style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                background-color:#ccc;text-align:center;">
                <table style="width:100%">
                    <tr>
                        <th>''' + _("System information") + ("       {" + pluginver + "}") + '''
                            <a onclick="var aboutheight = $('#about').height();                                        
                                        $('#ver_info').dialog({height: 200,width: 400,modal: false, show: 'explode'});
                                        $('#ver_info').animate({scrollTop: aboutheight },30000);
                                        $('#ver_info').animate({scrollTop: 0},1000);">
                                <span style="cursor: pointer;" title="''' + _('About') + '''">&#8505;</span>
                            </a>
                        </th>
                    </tr>
                    <tr>
                        <td style="text-align:center;">''' + _('Domoticz language is : {}').format(LANGTO) + '''
                            <a class="popup" href="''' + url_edit + '''&amp;file=''' + mpath + '''" target="adminframe">
                                <span style="cursor: pointer;" title="''' + _("Edit the lang file") + '''">
                                    &#9998;
                                </span>
                            </a>
                            <a class="devpopup" href="''' + url_lang + '''" target="adminframe">
                                <span style="cursor: pointer;" title="''' + _("Create or Update lang file") + '''">
                                    &#9881;
                                </span>
                            </a>
                            <!--
                            <a onclick="$('#webtrans').dialog({
                                                        height: 700,
                                                        width: 900,
                                                        modal: false,
                                                        position : { my: 'bottom', at: 'bottom', of: window },
                                                        show:'explode'});">
                                <span style="cursor: pointer;" title="''' + _('Translate') + '''">&#8617;</span>
                            </a>
                            -->
                        </td>
                    </tr>
                    <tr>
                        <td>''' + _('Domoticz, number of plugin devices : {}').format(str(nbrdev)) + ''' 
                        </td>
                    </tr>
                    <tr>
                        <td>''' + _('Domoticz, Hardware IDX : {}').format(str(hwidx)) + ''' 
                        </td>
                    </tr>
                    <tr>
                        <td>''' + _('HTTP Key : {}').format(str(URLKEY)) + ''' 
                        </td>
                    </tr>
                    <tr>    '''
    dataadmin = dataadmin + '''                        
                    </tr>
                </table>
            </div>
        </div>
        <div class="row">
            <div class="column" style="height:auto">
                <a onclick="window.open(this.href,this.target);return false;" href="''' + url_dir + '''" 
                target="adminframe">
                <button class="myButton" type="button" style="cursor: pointer;"
                    title="''' + _("Browse plugin folder") + '''">''' + _("Plugin directory") + '''
                </button>
                </a>'''
    if 'RM' in Parameters['Mode3']:
        dataadmin += '''
                <a onclick="window.open(this.href,this.target);return false;" 
                    href="''' + url_ini + '''" target="adminframe">
                    <button class="myButton" type="button" style="cursor: pointer;"
                        title="''' + _("Browse ini folder") + '''">''' + _("Ini directory") + '''</button>
                </a>'''
    dataadmin += '''
                <a onclick="window.open(this.href,this.target);return false;" 
                    href="''' + url_manage + '''" target="adminframe">
                    <button class="myButton" type="button" style="cursor: pointer;"
                        title="''' + _("Manage your device") + '''">''' + _("Manage") + '''</button>
                </a>
                <a onclick="document.location.reload(true);">
                    <button class="myButton" type="button" style="cursor: pointer;">''' + _("Refresh") + '''</button>
                </a>
            </div>
            <div class="column" style="height:auto">
            </div>
            <div id="content-mobile-3" class="column content-mobile" style="height:auto">
                <a class="popup" href="''' + url_log + '''" target="adminframe">
                    <button class="myButton" type="button" style="cursor: pointer;"
                    title="''' + _("Open plugin log") + '''">''' + _("Plugin Log") + '''</button>
                </a>
                <a class="devpopup" href="''' + url_chk + '''" target="adminframe">
                    <button class="myButton" type="button" style="cursor: pointer;"
                    title="''' + _("Check if new version is available") + '''">''' + _("Verify version") + '''</button>
                </a>
                <a onclick="updatePlugin()" target="adminframe">
                    <button class="myButton" type="button" style="cursor: pointer;"
                    title="''' + _("Update the plugin to current version") + '''">''' + _("Update") + '''</button>
                </a>
                <a onclick="backupPlugin()" target="adminframe">
                    <button class="myButton" type="button" style="cursor: pointer;"
                    title="''' + _("Backup plugin files to bkp folder") + '''">''' + _("Backup") + '''</button>
                </a>
            </div>
        </div>
        <div id="ezadminframe" style="text-align: center;padding: 20px;">
            <div id="ezUpl"></div>
        </div>
        
                    ''' + str(iframe) + '''
                    
        <div  style="display:none;"> 
            <form id="update_type" method="POST" target="adminframe" 
                    title="''' + _('Overwrite default device type') + '''" 
                    action="''' + url_post + "&amp;id='update_type'" + '''" 
                    enctype="application/x-www-form-urlencoded" 
                    onsubmit="return confirm(\'''' + msgconfirmd + '''\');">
                <label for="devtype" style="">''' + _("Select Device Type") + ''' 
                </label>
                <select id="devtype" name="devtype" required form="update_type">'''

    try:
        for x in brodevices:
            dev, group, manufacturer = brodevices[x]
            dataadmin += '''
                        <option value ="''' + str(x) + '''">''' + str(hex(x)) + " : " + group + " - " + \
                         manufacturer + '''</option>'''

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Not able to create list'))

    dataadmin += '''
                </select>
                <input class="myButton" type="submit" title="''' + _('Update device type') + '''"  
                value="''' + _('update') + \
                 '''" style="cursor: pointer;">
            </form>
        </div>
        <div id="about" style="display:none;">
            <address id="ver_info" title="''' + _('About') + '''">
        '''

    try:
        with open(fn, 'r', encoding='utf-8') as pf:
            for line in pf:
                if line.startswith('<plugin'):
                    break

                else:

                    verinfo += line + '<br>'

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('Not able to read  : {}').format(fn))

    dataadmin += verinfo
    dataadmin += '''
            </address>
        </div>
        <div id="webtrans" style="display:none">
            <iframe style="border: 0px; " src="''' + url_trans + '''" width="100%" height="100%"></iframe>'
        </div>
        <div id='scroll_to_top' >
            <a title="Top">
                <span style="cursor: pointer;background-color:rgba(255, 99, 5, 0.7);color:black;font-size:45px;">
                &#8686;
                </span>
            </a>
        </div>
    </body>
</html> 
'''
    return dataadmin


#
# create html for directory browse
#
def list_directory(mypath, button):
    global DISPLAYPATH
    """
    Helper to produce a directory listing.

    """

    # read folder content
    try:
        ilist = os.listdir(mypath)

    except os.error:
        Domoticz.Error(traceback.format_exc())
        Domoticz.Log(mypath)
        Domoticz.Error(_("No permission to list directory"))

        return

    # sort content
    ilist.sort(key=lambda a: a.lower())

    DISPLAYPATH = html.escape(urllib.parse.unquote(mypath))

    # create html
    htm = '''<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <title>Domoticz Broadlink</title>
        <link rel="icon" href="data:,"/>
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + '''/web/css/button.css" 
            rel = "stylesheet">
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
        '''/web/js/sorttable.js"></script>

'''
    if autoresize:
        htm += '''
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/iframeResizer.contentWindow.js"></script>
'''
    htm += '''
        <style>
         
        /* Sortable tables */
        table.sortable thead {
            background-color:#eee;            
            color:#666666;
            font-weight: bold;
            cursor: grab;
        }

        .myrow {
            background-color: whitesmoke;
        }
        .myrow:hover {	
            box-shadow: 0 0 20px 20px rgb(2, 16, 21);
            background-color: white;
            text-decoration: underline overline gray;
        }
        a:link {
            color: red;
        }
        /* visited link */
        a:visited {
            background-color: gray;
        }
        /* mouse over link */
        a:hover {
            background-color: #d0bd54;
        }
        /* selected link */        
        a:active {
            color: white;
            background-color: blueviolet;
        }
        
        table, th, td {
            border: 1px solid white;
            border-collapse: collapse;
        }
        th, td {
            padding: 1px;
        }
   
        </style>
    </head>
    <body>
        <h2 style="background-color:whitesmoke;text-align:center;color:''' + colorstate(1) + ''';">
            Domoticz Broadlink Plugin
        </h2>
        <hr>
        '''

    htm = htm + '''
    <h3 style="background-color:whitesmoke;">''' + _("Directory content for : {} ").format(DISPLAYPATH) + ''' </h3>\n
        '''

    if button:
        htm = htm + '''
        <input class="myButton" type="button" value="''' + _("Go back") + '''" onclick="history.back()">
        '''

    htm = htm + '''
        <hr>\n
        <hr>\n
        <table class="sortable" style="width:100%;box-shadow: 0px 10px 14px -7px #276873;font-family:monospace;">
        <tr style="background-color:yellow;">
            <th>''' + _('Name') + '''</th>
            <th>''' + _('Size') + '''</th>
            <th>''' + _('Date') + '''</th>
        </tr>
        '''

    for name in ilist:
        fullname = os.path.join(mypath, name)
        displayname = linkname = name

        modtimesinceepoc = os.path.getmtime(fullname)
        modificationtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modtimesinceepoc))
        size = os.stat(fullname).st_size

        # Append / for directories or @ for symbolic links
        if os.path.isdir(fullname):
            displayname = name + "/"
            linkname = name + "/"
            size = '<a href="' + urllib.parse.quote(linkname) + '">&#128193;</a>'
        if os.path.islink(fullname):
            displayname = name + "@"
            # Note: a link to a directory displays with @ and links with /
        htm = htm + \
            ('<tr class="myrow">'
             '<td class="myrow"><a href="%s">%s</a></td>'
             '<td style="background-color:white;">%s</td>'
             '<td style="background-color:white;">%s\n</td>'
             '</tr>'
             % (urllib.parse.quote(linkname), html.escape(displayname), size, modificationtime))

    htm = htm + "</table><hr>\n</body>\n</html>\n"

    return htm


#
# Display Domoticz log data related to the plugin
#
def domo_log():
    params = {'type': 'command', 'param': 'getlog', 'loglevel': '268435455'}
    txt = ''

    if exe_domoticz(params):
        if DOMDATA['status'] == 'OK':
            if 'result' in DOMDATA:
                result = DOMDATA['result']
                for items in result:
                    if Parameters['Name'] in items['message']:
                        if 'Error' in items['message']:
                            txt += '<span style="color: red;">' + (items['message']) + '</span>' + '\n'

                        elif 'Status:' in items['message']:
                            txt += '<span style="color: orange;">' + '<b>' + (items['message']) + '</b></span>' + '\n'

                        else:

                            txt += (items['message']) + '\n'

            else:

                txt = "ERROR Domoticz Log"

        else:

            txt = "ERROR Domoticz Log"

    else:

        txt = "ERROR Domoticz Log"

    datafile = '''<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <title>Broadlink Log Viewer</title>
        <link rel="icon" href="data:,"/>
'''
    if autoresize:
        datafile += '''
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                    '''/web/js/iframeResizer.contentWindow.js"></script>
'''
    datafile += '''
    </head>
    <body style="background-color:whitesmoke;">
        <hr>
        <p style="white-space: pre-line;">''' + txt + '''</p>
    </body>
</html>'''

    return datafile


#
# we generate Editor for file modification
#
def html_editor(fname):
    msgconfirm = _('Are you sure you want to update data ?')

    try:
        with open(fname, 'r', encoding='utf-8') as fp:
            line = fp.read()

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('File not exist or problem to access : {}').format(str(fname)))

        return False

    htmledit = '''<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <link rel="icon" href="data:,"/>
        <title>Broadlink file Editor</title>
        <style type="text/css" media="screen">
            table, th, td {
                border: 1px solid white;
                border-collapse: collapse;
            }
            th, td {
                padding: 1px;
            }
            .mysc {
                text-align:center;
                font-size:70%;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
                background-color:#aaa;
            }
            .ace_editor {
                position: relative !important;
                border: 1px solid lightgray;
                margin: auto;
                height: 100%;
                width: 100%;
            }
            .ace_editor.fullScreen {
                height: auto;
                width: auto;
                border: 0;
                margin: 0;
                position: fixed !important;
                top: 0;
                bottom: 0;
                left: 0;
                right: 0;
                z-index: 10;
            }
            .fullScreen {
                overflow: hidden
            }
            body {
                transform: translateZ(0);
            }
        </style>
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/jquery-3.4.1.min.js"></script>
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/jquery-ui.min.js"></script>
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/ace/ace.js" type="text/javascript" charset="utf-8"></script>
'''
    if autoresize:
        htmledit += '''
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                    '''/web/js/iframeResizer.contentWindow.js"></script>
'''
    htmledit += '''
    </head>
    <body>
<!-- 
Div for editor menu / action
-->
        <div id="menu">
            <h2 style="background-color:whitesmoke;text-align:center;color:''' + colorstate(1) + ''';">
                Broadlink On-Line Editor : ''' + fname + '''
            </h2>               
            <div style="text-align:right;">
                <form id="upload_form" enctype="multipart/form-data" method="post" target="adminframe">
                <input type="hidden" name="''' + fname + '''" id="ezlngdata">
                <input class="myButton" type="button" value="''' + _("update") + '''" 
                    style="cursor: pointer;" onclick="save();">
                </form>
            </div>
            <a onclick="find();">
                <button type="button" style="cursor: pointer;">''' + _("search") + '''</button>
            </a>
            <a onclick="replace();">
                <button type="button" style="cursor: pointer;">''' + _("replace") + '''</button>
            </a>
            <a onclick="undo();">
                <button type="button" style="cursor: pointer;">''' + _("undo") + '''</button>
            </a>
            <a onclick="redo();">
                <button type="button" style="cursor: pointer;">''' + _("redo") + '''</button>
            </a>
            <a onclick="toggleFullScreen();">
                <button type="button" style="cursor: pointer;">''' + _("FullScreen") + '''</button>
            </a>
            <a onclick="edtsc();">
                <button type="button" style="cursor: pointer;">''' + "?" + '''</button>
                <div id="edtsc" class="mysc" style="display:none;">''' + editor_shortcuts() + '''</div>
            </a>
        </div>
<!-- 
Main div with content to edit
-->
        <div id="ezdata" style="width:100%;height:300px;">'''

    htmledit = htmledit + line

    htmledit += '''</div>

<!-- 
Main script to manage ACE editor
-->
        <script>

        
            var editor = ace.edit("ezdata");
            var mydata = "";
            editor.session.setMode("ace/mode/python");
            editor.setOptions({
                theme: "ace/theme/monokai",
                autoScrollEditorIntoView: true,
                showPrintMargin: false,
                });
           function edtsc() {
                $("#edtsc").toggle(2000);
                }     
            function undo() {
                editor.undo();
                }
            function redo() {
                editor.redo();
                }
            function find() {
                editor.execCommand("find")
                }
            function replace() {
                editor.execCommand("replace")
                }
            function fullscreen() {
                editor.container.webkitRequestFullscreen()
                }
            function save() {
                if (confirm(\'''' + msgconfirm + '''\')){
                    var mydata = editor.getSession().getValue();
                    $("#ezlngdata").val(mydata);
                    $("#upload_form").submit();
                    }
                }
            var editorElement = document.getElementById("ezdata");    
            function toggleFullScreen() {
            if (!document.mozFullScreen && !document.webkitFullScreen) {
                if (editorElement.mozRequestFullScreen) {
                editorElement.mozRequestFullScreen();
                } else {
                editorElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
                }
            } else {
                if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
                } else {
                document.webkitCancelFullScreen();
                }
            }
            }
            document.addEventListener("keydown", function(e) {
            if (e.keyCode == 7) {
                toggleFullScreen();
            }
            }, false);

        </script>
<!-- 
Main script to manage ACE editor
-->

    </body>
</html>
'''
    return htmledit


#
# Ace editor shortcuts help
#
def editor_shortcuts():
    htmled = '''
<h2>Line Operations</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Ctrl-D</td>
<td align="left">Command-D</td>
<td align="left">Remove line</td>
</tr>
<tr>
<td align="left">Alt-Shift-Down</td>
<td align="left">Command-Option-Down</td>
<td align="left">Copy lines down</td>
</tr>
<tr>
<td align="left">Alt-Shift-Up</td>
<td align="left">Command-Option-Up</td>
<td align="left">Copy lines up</td>
</tr>
<tr>
<td align="left">Alt-Down</td>
<td align="left">Option-Down</td>
<td align="left">Move lines down</td>
</tr>
<tr>
<td align="left">Alt-Up</td>
<td align="left">Option-Up</td>
<td align="left">Move lines up</td>
</tr>
<tr>
<td align="left">Alt-Delete</td>
<td align="left">Ctrl-K</td>
<td align="left">Remove to line end</td>
</tr>
<tr>
<td align="left">Alt-Backspace</td>
<td align="left">Command-Backspace</td>
<td align="left">Remove to linestart</td>
</tr>
<tr>
<td align="left">Ctrl-Backspace</td>
<td align="left">Option-Backspace, Ctrl-Option-Backspace</td>
<td align="left">Remove word left</td>
</tr>
<tr>
<td align="left">Ctrl-Delete</td>
<td align="left">Option-Delete</td>
<td align="left">Remove word right</td>
</tr>
<tr>
<td align="left">---</td>
<td align="left">Ctrl-O</td>
<td align="left">Split line</td>
</tr>
</tbody>
</table>
<h2>Selection</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Ctrl-A</td>
<td align="left">Command-A</td>
<td align="left">Select all</td>
</tr>
<tr>
<td align="left">Shift-Left</td>
<td align="left">Shift-Left</td>
<td align="left">Select left</td>
</tr>
<tr>
<td align="left">Shift-Right</td>
<td align="left">Shift-Right</td>
<td align="left">Select right</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-Left</td>
<td align="left">Option-Shift-Left</td>
<td align="left">Select word left</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-Right</td>
<td align="left">Option-Shift-Right</td>
<td align="left">Select word right</td>
</tr>
<tr>
<td align="left">Shift-Home</td>
<td align="left">Shift-Home</td>
<td align="left">Select line start</td>
</tr>
<tr>
<td align="left">Shift-End</td>
<td align="left">Shift-End</td>
<td align="left">Select line end</td>
</tr>
<tr>
<td align="left">Alt-Shift-Right</td>
<td align="left">Command-Shift-Right</td>
<td align="left">Select to line end</td>
</tr>
<tr>
<td align="left">Alt-Shift-Left</td>
<td align="left">Command-Shift-Left</td>
<td align="left">Select to line start</td>
</tr>
<tr>
<td align="left">Shift-Up</td>
<td align="left">Shift-Up</td>
<td align="left">Select up</td>
</tr>
<tr>
<td align="left">Shift-Down</td>
<td align="left">Shift-Down</td>
<td align="left">Select down</td>
</tr>
<tr>
<td align="left">Shift-PageUp</td>
<td align="left">Shift-PageUp</td>
<td align="left">Select page up</td>
</tr>
<tr>
<td align="left">Shift-PageDown</td>
<td align="left">Shift-PageDown</td>
<td align="left">Select page down</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-Home</td>
<td align="left">Command-Shift-Up</td>
<td align="left">Select to start</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-End</td>
<td align="left">Command-Shift-Down</td>
<td align="left">Select to end</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-D</td>
<td align="left">Command-Shift-D</td>
<td align="left">Duplicate selection</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-P</td>
<td align="left">---</td>
<td align="left">Select to matching bracket</td>
</tr>
</tbody>
</table>
<h2>Multicursor</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Ctrl-Alt-Up</td>
<td align="left">Ctrl-Option-Up</td>
<td align="left">Add multi-cursor above</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Down</td>
<td align="left">Ctrl-Option-Down</td>
<td align="left">Add multi-cursor below</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Right</td>
<td align="left">Ctrl-Option-Right</td>
<td align="left">Add next occurrence to multi-selection</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Left</td>
<td align="left">Ctrl-Option-Left</td>
<td align="left">Add previous occurrence to multi-selection</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Shift-Up</td>
<td align="left">Ctrl-Option-Shift-Up</td>
<td align="left">Move multicursor from current line to the line above</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Shift-Down</td>
<td align="left">Ctrl-Option-Shift-Down</td>
<td align="left">Move multicursor from current line to the line below</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Shift-Right</td>
<td align="left">Ctrl-Option-Shift-Right</td>
<td align="left">Remove current occurrence from multi-selection and move to next</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-Shift-Left</td>
<td align="left">Ctrl-Option-Shift-Left</td>
<td align="left">Remove current occurrence from multi-selection and move to previous</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-L</td>
<td align="left">Ctrl-Shift-L</td>
<td align="left">Select all from multi-selection</td>
</tr>
</tbody>
</table>
<h2>Go to</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Left</td>
<td align="left">Left, Ctrl-B</td>
<td align="left">Go to left</td>
</tr>
<tr>
<td align="left">Right</td>
<td align="left">Right, Ctrl-F</td>
<td align="left">Go to right</td>
</tr>
<tr>
<td align="left">Ctrl-Left</td>
<td align="left">Option-Left</td>
<td align="left">Go to word left</td>
</tr>
<tr>
<td align="left">Ctrl-Right</td>
<td align="left">Option-Right</td>
<td align="left">Go to word right</td>
</tr>
<tr>
<td align="left">Up</td>
<td align="left">Up, Ctrl-P</td>
<td align="left">Go line up</td>
</tr>
<tr>
<td align="left">Down</td>
<td align="left">Down, Ctrl-N</td>
<td align="left">Go line down</td>
</tr>
<tr>
<td align="left">Alt-Left, Home</td>
<td align="left">Command-Left, Home, Ctrl-A</td>
<td align="left">Go to line start</td>
</tr>
<tr>
<td align="left">Alt-Right, End</td>
<td align="left">Command-Right, End, Ctrl-E</td>
<td align="left">Go to line end</td>
</tr>
<tr>
<td align="left">PageUp</td>
<td align="left">Option-PageUp</td>
<td align="left">Go to page up</td>
</tr>
<tr>
<td align="left">PageDown</td>
<td align="left">Option-PageDown, Ctrl-V</td>
<td align="left">Go to page down</td>
</tr>
<tr>
<td align="left">Ctrl-Home</td>
<td align="left">Command-Home, Command-Up</td>
<td align="left">Go to start</td>
</tr>
<tr>
<td align="left">Ctrl-End</td>
<td align="left">Command-End, Command-Down</td>
<td align="left">Go to end</td>
</tr>
<tr>
<td align="left">Ctrl-L</td>
<td align="left">Command-L</td>
<td align="left">Go to line</td>
</tr>
<tr>
<td align="left">Ctrl-Down</td>
<td align="left">Command-Down</td>
<td align="left">Scroll line down</td>
</tr>
<tr>
<td align="left">Ctrl-Up</td>
<td align="left">---</td>
<td align="left">Scroll line up</td>
</tr>
<tr>
<td align="left">Ctrl-P</td>
<td align="left">---</td>
<td align="left">Go to matching bracket</td>
</tr>
<tr>
<td align="left">---</td>
<td align="left">Option-PageDown</td>
<td align="left">Scroll page down</td>
</tr>
<tr>
<td align="left">---</td>
<td align="left">Option-PageUp</td>
<td align="left">Scroll page up</td>
</tr>
</tbody>
</table>
<h2>Find/Replace</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Ctrl-F</td>
<td align="left">Command-F</td>
<td align="left">Find</td>
</tr>
<tr>
<td align="left">Ctrl-H</td>
<td align="left">Command-Option-F</td>
<td align="left">Replace</td>
</tr>
<tr>
<td align="left">Ctrl-K</td>
<td align="left">Command-G</td>
<td align="left">Find next</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-K</td>
<td align="left">Command-Shift-G</td>
<td align="left">Find previous</td>
</tr>
</tbody>
</table>
<h2>Folding</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Alt-L, Ctrl-F1</td>
<td align="left">Command-Option-L, Command-F1</td>
<td align="left">Fold selection</td>
</tr>
<tr>
<td align="left">Alt-Shift-L, Ctrl-Shift-F1</td>
<td align="left">Command-Option-Shift-L, Command-Shift-F1</td>
<td align="left">Unfold</td>
</tr>
<tr>
<td align="left">Alt-0</td>
<td align="left">Command-Option-0</td>
<td align="left">Fold all</td>
</tr>
<tr>
<td align="left">Alt-Shift-0</td>
<td align="left">Command-Option-Shift-0</td>
<td align="left">Unfold all</td>
</tr>
</tbody>
</table>
<h2>Other</h2>
<table>
<thead>
<tr>
<th align="left">Windows/Linux</th>
<th align="left">Mac</th>
<th align="left">Action</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Tab</td>
<td align="left">Tab</td>
<td align="left">Indent</td>
</tr>
<tr>
<td align="left">Shift-Tab</td>
<td align="left">Shift-Tab</td>
<td align="left">Outdent</td>
</tr>
<tr>
<td align="left">Ctrl-Z</td>
<td align="left">Command-Z</td>
<td align="left">Undo</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-Z, Ctrl-Y</td>
<td align="left">Command-Shift-Z, Command-Y</td>
<td align="left">Redo</td>
</tr>
<tr>
<td align="left">Ctrl-,</td>
<td align="left">Command-,</td>
<td align="left">Show the settings menu</td>
</tr>
<tr>
<td align="left">Ctrl-/</td>
<td align="left">Command-/</td>
<td align="left">Toggle comment</td>
</tr>
<tr>
<td align="left">Ctrl-T</td>
<td align="left">Ctrl-T</td>
<td align="left">Transpose letters</td>
</tr>
<tr>
<td align="left">Ctrl-Enter</td>
<td align="left">Command-Enter</td>
<td align="left">Enter full screen</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-U</td>
<td align="left">Ctrl-Shift-U</td>
<td align="left">Change to lower case</td>
</tr>
<tr>
<td align="left">Ctrl-U</td>
<td align="left">Ctrl-U</td>
<td align="left">Change to upper case</td>
</tr>
<tr>
<td align="left">Insert</td>
<td align="left">Insert</td>
<td align="left">Overwrite</td>
</tr>
<tr>
<td align="left">Ctrl-Shift-E</td>
<td align="left">Command-Shift-E</td>
<td align="left">Macros replay</td>
</tr>
<tr>
<td align="left">Ctrl-Alt-E</td>
<td align="left">---</td>
<td align="left">Macros recording</td>
</tr>
<tr>
<td align="left">Delete</td>
<td align="left">---</td>
<td align="left">Delete</td>
</tr>
<tr>
<td align="left">---</td>
<td align="left">Ctrl-L</td>
<td align="left">Center selection</td></tr></tbody></table>
'''

    return htmled


#
# Create html for file output into browser or for download
#
def readf(mpath, todownload, toback=True):
    if todownload:
        try:
            with open(mpath, 'r+b') as file:
                datafile = file.read()

        except IOError:

            return '<span style="background-color:whitesmoke;">' + _("File not found") + '</span>'
    else:

        try:
            with open(mpath, 'r', encoding='utf-8') as file:
                txt = file.read()

        except IOError:

            return '<span style="background-color:whitesmoke;">' + _("File not found") + '</span>'

        datafile = '''<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <title>Broadlink File Viewer</title>
        <link rel="icon" href="data:,"/>
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + '''/web/css/button.css" 
            rel = "stylesheet">
'''
        if autoresize:
            datafile += '''
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                    '''/web/js/iframeResizer.contentWindow.js"></script>
'''
        datafile += '''   
    </head>
    <body style="background-color:whitesmoke;">
'''
        if toback:
            datafile += '''
        <input class="myButton" type="button" value="''' + _("Go back") + '''" 
            onclick="history.back()" style="position: fixed">
'''
        datafile += '''
        <hr>
        <br>
        <p style="white-space: pre-line;">
        ''' + txt + '''
        </p>
    </body>
</html>
'''
    return datafile


#
# Broadlink device information & graphics
# ini file content
#
def manage():
    import fnmatch

    myini = []
    refresh = True
    sec = 30
    url = 'manage'
    repeat = 0
    msgconfirmu = _('Are you sure you want to delete Ini file and all related data ?')
    msgconfirm = _('Are you sure ?')

    if 1 in Devices:
        domunit = str(Devices[int(1)].ID)
        customdev(domunit)

    else:

        Domoticz.Error(_('Device 1 not exist'))
        return '<span style="background-color:whitesmoke;">' + _('Device 1 not exist') + '</span>'

    is_locked = '***'
    brotype = '***'
    brofw = '***'
    manu = '***'
    devtype = '***'

    try:
        if hasattr(DEVICE, 'is_locked'):
            is_locked = str(DEVICE.is_locked)

        if hasattr(DEVICE, 'get_type'):
            brotype = str(DEVICE.get_type())

        if hasattr(DEVICE, 'get_fwversion'):
            brofw = str(DEVICE.get_fwversion())

        if hasattr(DEVICE, 'manufacturer'):
            manu = str(DEVICE.manufacturer)

        if hasattr(DEVICE, 'devtype'):
            devtype = hex(DEVICE.devtype)

    except (ValueError, Exception):
        if INFOLEVEL > 0:
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error retrieve data from device : {}').format(domunit))
        pass

    url_ectrl = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/eControl?key=' + URLKEY
    url_import = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/import?key=' + URLKEY
    url_scan = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/scanDevices?key=' + URLKEY
    url_usage = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/usageDevices?key=' + URLKEY
    url_edit = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/iniEditor?key=' + URLKEY
    url_send = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/sendCode?key=' + URLKEY
    url_cred = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/createDevice?key=' + URLKEY
    url_multi = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/multiCode?key=' + URLKEY
    url_ircode = 'http://irdb.tk/find/'
    url_post = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/postupdDatas?key=' + URLKEY
    url_dome = 'http://' + Parameters['Address'] + ':' + Parameters['Port'] + '/#/Devices/' + str(domunit) + \
               '/LightEdit'
    url_learnir = ''
    url_learnrf = ''

    # read folder content, search for ini files, create HTML for device (IR/RF)
    if 'RM2' in Parameters['Mode3']:
        try:
            ilist = os.listdir(Parameters['Mode2'])
            inipath = "*" + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + "-*.ini"
            for file in ilist:
                if fnmatch.fnmatch(file, inipath):
                    myini.append(file)

            myini.sort(key=lambda a: a.lower())

        except os.error:

            return '<span style="background-color:whitesmoke;">' + _("No permission to list directory") + '</span>'

        if 2 in Devices:
            domunit = str(Devices[int(2)].ID)
            customdev(domunit)
            url_learnir = 'http://' + Parameters['Address'] + ':' + Parameters['Port'] + '/#/Custom/' + 'Broadlink-' + \
                          Parameters['Mode3'] + '-' + str(Parameters["HardwareID"]) + '-' + str(domunit)

        if 3 in Devices:
            domunit = str(Devices[int(3)].ID)
            customdev(domunit)
            url_learnrf = 'http://' + Parameters['Address'] + ':' + Parameters['Port'] + '/#/Custom/' + 'Broadlink-' + \
                          Parameters['Mode3'] + '-' + str(Parameters["HardwareID"]) + '-' + str(domunit)

    datafile = '''<!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8"/>
            <title>Broadlink Devices</title>
            <link rel="icon" href="data:,"/>
            <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/css/ui-darkness/jquery-ui.min.css" rel = "stylesheet">
            <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/css/manage.css" rel = "stylesheet">

            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/jquery-3.4.1.min.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/jquery-ui.min.js"></script>

            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.common.core.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.thermometer.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.meter.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.vprogress.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.odo.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.fuel.js"></script>
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/RGraph.gauge.js"></script>

'''
    if autoresize:
        datafile += '''
            <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                    '''/web/js/iframeResizer.contentWindow.js"></script>
'''
    datafile += '''
                
        <script>
  
            $(document).ready(function(){
                            
                var newver = "''' + NEWPLUGIN + '''";
                if ( newver === "yes" ) { 
                            $("#resultat").html("<span>...''' + _("New version available") + '''</span>"); 
                            };
                            
                $(document).tooltip();

                $(".popup").click(function (event) {
                    event.preventDefault();
                    var page = $(this).attr("href");
                    var title = $(this).text();
                    var windowsize = $(window).width();
                    seconds = 360;
                    if (windowsize > 1020) {
                        //if the window is greater than 1020px wide then open dialog..
                        //alert('> 1024');
                        $('<div></div>')
                        .html('<iframe style="border: 0px; " src="' + page + '" width="100%" height="100%"></iframe>')
                        .dialog({
                            autoOpen: true,
                            modal: false,
                            height: 600,
                            width: 900,
                            title: title,
                            show: 'slideDown',
                            position : { my: "top", at: "top", of: event },
                            close: function( event, ui ) { seconds = 5;}                          
                                });
                                
                        } else {
                        //alert('< 1024');
                        window.open(this.href, this.target);
                    }
                });
                $(".devpopup").click(function (event) {
                    event.preventDefault();
                    var page = $(this).attr("href");
                    var title = $(this).text();
                    var windowsize = $(window).width();
                    seconds = 360;
                    if (windowsize > 600) {
                        //if the window is greater than 1020px wide then open dialog..
                        //alert('> 1024');
                        $('<div></div>')
                        .html('<iframe style="border: 0px; " src="' + page + '" width="100%" height="100%"></iframe>')
                        .dialog({
                            autoOpen: true,
                            modal: false,
                            height: 400,
                            width: 600,
                            title: title,
                            show: 'slideDown',
                            position : { my: "top", at: "top", of: window },
                            close: function( event, ui ) {window.location.reload();}                          
                                });
                                
                        } else {
                        //alert('< 1024');
                        window.open(this.href, this.target);
                    }
                });
                
                function scroll_to_top(div) {
                    $(div).click(function() {
                        $('html,body').animate({scrollTop: 0}, 'slow');
                    });
                    $(window).scroll(function(){
                        if($(window).scrollTop()<200){
                            $(div).fadeOut();
                        } else{
                            $(div).fadeIn();
                        }
                    });
                }
                scroll_to_top("#scroll_to_top");                    
                
            });
            
            $(function(){
                $("#accordion").accordion({
                    collapsible: true,
                    heightStyle: "content",
                    icons: false
                                            });
            });
        </script>
            
        </head>
        <body style="background-color:whitesmoke;">'''
    if 'RM2' in Parameters['Mode3']:
        datafile += '''
        <script>
            $(document).ready(function(){
                $("#import").click(function(e){
                    e.preventDefault();
                    $.get(
                        "''' + url_import + '''",
                        {
                        },
                        function(data){
                           $("#resultat").html("<span>...''' + _('... Verify import result ...') + '''</span>");
                        },
                        "text"
                     );
                });
                $("#econtrol").click(function(e){
                    e.preventDefault();
                    $.get(
                        "''' + url_ectrl + '''",
                        {
                        },
                        function(data){
                           $("#resultat").html("<span>...''' + _('... Verify ini generation ...') + '''</span>");
                        },
                        "text"
                     );
                });
            });
        </script>'''
    datafile += '''
            <hr>
            <div id="accordion">
                <h3 style="color:''' + (colorstate(1)) + ''';">''' + Devices[1].Name + "-" + devtype + ''' </h3>
                <div>
                <span>''' + _("Device information for Broadlink type : ") + '''</span>
                <span style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5);background-color:#fff;text-align: center;">
                 [''' + Parameters["Mode3"] + '''] </span>
                    <div class="row">
                        <div class="column">
                            <ul>
                                <li>IP  : ''' + Parameters["Mode4"] + '''</li>
                                <li>MAC : ''' + Parameters["Mode1"] + '''</li>
                                <li>Type: ''' + brotype + '''</li>
                                <li class="media-mobile">Manufacturer: ''' + manu + '''</li>
                                <li class="media-mobile">Locked: ''' + is_locked + '''</li>
                                <li class="media-mobile">Firmware: ''' + brofw + '''</li>
                                <li class="media-mobile">Plugin Unit: ''' + "1" + '''</li>
                                <li class="media-mobile">Domoticz IDX: ''' + str(Devices[1].ID) + '''
                                    <a  class="popup"  href="''' + url_dome + '''" title="Go">
                                        <span style="cursor: pointer;background-color:#aaa;">&#8635;</span>
                                    </a></li>
                                <li style="color:''' + (colorstate(1)) + ''';">State: ''' + Devices[1].sValue + '''</li>
                            </ul>
                        </div>
                        <div>
                            <hr>                            
                            <a class="devpopup" href="''' + url_scan + '''" target="adminframe"
                                title = "''' + _("Scan Broadlink devices") + '''">                    
                                <button type="button" class="ui-button ui-corner-all">''' + _("Network scan") + '''
                                </button>
                            </a>'''
    if 'RM' in Parameters['Mode3']:
        datafile += '''
                            <a class="media-mobile devpopup" href="''' + url_usage + '''" target="adminframe"
                                title = "''' + _("Show Broadlink usage and devices linked") + '''">                    
                                <button type="button" class="ui-button ui-corner-all">''' + _("Usage") + '''
                                </button>
                            </a>
                            <a class="popup" href="''' + url_multi + '''" target="adminframe"
                                title = "''' + _('Create ini file for send more than one code RF / IR') + '''">
                                <button type="button" class="ui-button ui-corner-all">''' + _("Multi-Code") + '''
                                </button>
                            </a>
                            <a class="devpopup" href="''' + url_learnir + '''" target="adminframe"
                                title = "''' + _("Learn / Create IR code") + '''">                    
                                <button type="button" class="ui-button ui-corner-all">''' + _("Learn IR") + '''
                                </button>
                            </a>
                    '''
        if not Parameters['Mode3'].endswith('M'):
            datafile += '''
                            <a class="devpopup" href="''' + url_learnrf + '''" target="adminframe"
                                title = "''' + _("Learn / Create RF code") + '''">                    
                                <button type="button" class="ui-button ui-corner-all">''' + _("Learn RF") + '''
                                </button>
                            </a>
                    '''
    datafile += '''
                            <hr>'''
    if Parameters['Mode3'] == 'SP3S':
        sec = 5
        check_power()
        usedw = 0
        todayw = 0
        if 3 in Devices:
            try:
                todayw = float(Devices[3].sValue.split(';')[1]) / 1000
            except (ValueError, Exception):
                todayw = 0
                Domoticz.Error(_('Not able to retrieve data for Usage kWh -- verify device'))
        if 2 in Devices:
            usedw = Devices[2].sValue
        datafile += '''
                            <canvas id="cvs" width="250" height="250" style="float: left;" 
                            title = "''' + usedw + '''">
                                [No canvas support]
                            </canvas>

                            <script>
                                new RGraph.Gauge({
                                    id: 'cvs',
                                    min: 0,
                                    max: 3520,
                                    value:''' + usedw + ''',
                                    options: {
                                        titleTop: 'Current',
                                        titleTopBold: true,
                                        titleBottom : 'Watt',                                        
                                        labelsSize: 8,
                                        marginLeft: 15,
                                        marginRight: 15,
                                        marginTop: 15,
                                        marginBottom: 15
                                    }
                                }).draw().responsive([{maxWidth: 800,width:140,height:140,
                                                       options:{marginLeft:1,
                                                                marginRight: 1,
                                                                marginTop: 5,
                                                                marginBottom:5,
                                                                labelsSize: 5,
                                                                titleTopSize : 6,
                                                                titleBottomSize : 6}},
                                                      {maxWidth: null,width:250,height:250,
                                                       options:{marginLeft:15,
                                                                marginRight: 15,
                                                                marginTop: 15,
                                                                marginBottom: 15}}]);
                            </script>
                            
                            <canvas id="cvs2" width="250" height="250" style="float: left;"
                            title = "''' + str(todayw) + '''">                            
                                [No canvas support]
                            </canvas>

                            <script>
                                new RGraph.Gauge({
                                    id: 'cvs2',
                                    min: 0,
                                    max: 20,
                                    value: ''' + str(todayw) + ''',
                                    options: {
                                        titleTop: 'Usage',
                                        titleTopBold: true,
                                        titleBottom : 'kWh',
                                        scaleDecimals : 2,
                                        labelsSize: 8,
                                        marginLeft: 15,
                                        marginRight: 15,
                                        marginTop: 15,
                                        marginBottom: 15
                                    }
                                }).draw().responsive([{maxWidth: 800,width:140,height:140,
                                                       options:{marginLeft:1,
                                                                marginRight: 1,
                                                                marginTop: 5,
                                                                marginBottom:5,
                                                                labelsSize: 5,
                                                                titleTopSize : 6,
                                                                titleBottomSize : 6}},
                                                      {maxWidth: null,width:250,height:250,
                                                       options:{marginLeft:15,
                                                                marginRight: 15,
                                                                marginTop: 15,
                                                                marginBottom: 15}}]);
                            </script>
                            '''
    elif 'RM' in Parameters['Mode3'] or Parameters['Mode3'] == 'A1':
        if hasattr(DEVICE, 'check_temperature') and ISCONNECTED:
            check_temp()
        elif Parameters['Mode3'] == 'A1':
            check_sensor()
        datafile += '''
                            <canvas id="cvs" width="65" height="200" style="float: left;">
                                [No canvas support]
                            </canvas>

                            <script>
                                my1 = new RGraph.Thermometer({
                                    id: 'cvs',
                                    min: -10,
                                    max: 50,
                                    value: ''' + str(TEMP) + ''',
                                    options: {
                                        titleSide: "°C",
                                        titleSideBold: true,
                                        scaleVisible: true,
                                        labelsValueDecimals: 1,
                                        marginLeft: 25,
                                        marginRight: 25,
                                        marginTop: 25,
                                        marginBottom: 25,
                                        textSize : 7,
                                        highlightStyle: true
                                    }
                                }).grow().responsive([{maxWidth: 800,width:20,height:80,
                                                       options:{marginLeft:5,
                                                                marginRight: 5,
                                                                marginTop: 5,
                                                                marginBottom: 5}},
                                                      {maxWidth: null,width:65,height:200,
                                                       options:{marginLeft:25,
                                                                marginRight: 25,
                                                                marginTop: 25,
                                                                marginBottom: 25}}]);
                            </script>'''
    elif Parameters['Mode3'] == 'SP2':
        url_on = 'http://' + Parameters['Address'] + ':' + Parameters['Port'] + \
                 '/json.htm?type=command&param=switchlight&switchcmd=On&idx=' + str(Devices[1].ID)
        url_off = 'http://' + Parameters['Address'] + ':' + Parameters['Port'] + \
                  '/json.htm?type=command&param=switchlight&switchcmd=Off&idx=' + str(Devices[1].ID)
        if Devices[1].sValue == 'On':
            onoff = 'checked'

        else:

            onoff = ' '

        datafile += '''     <label class="switch" title = "''' + _("Click to switch") + '''">
                                <input id="onoff" type="checkbox" ''' + onoff + '''>
                                <span class="slider round"></span>
                            </label>
                            <h2>Off/On</h2>
                            <script>
                                var OnOff = document.querySelector('input[id="onoff"]');
                                OnOff.onchange = function() {
                                  if(OnOff.checked) {
                                    // On
                                    $.get("''' + url_on + '''");
                                    setTimeout(function(){ location.reload(); }, 1000);
                                  } else {
                                    // Off
                                    $.get("''' + url_off + '''");
                                    setTimeout(function(){ location.reload(); }, 1000);
                                  }
                                };
                            </script>
                            '''
    if Parameters['Mode3'] == 'A1':
        meter = 0
        progress = '0'
        odometer = 0
        fuel = '0'
        if 3 in Devices:
            meter = Devices[3].nValue
        if 6 in Devices:
            progress = Devices[6].sValue
        if 4 in Devices:
            odometer = Devices[4].nValue
        if 5 in Devices:
            fuel = Devices[5].sValue

        datafile += '''
                            <canvas id="cvs2" width="200" height="200" style="float: left;">
                                [No canvas support]
                            </canvas>
                            
                            <script>                 
                                my2 = new RGraph.Meter({
                                    id: 'cvs2',
                                    min: 0,
                                    max: 100,
                                    value: ''' + str(meter) + ''',
                                    options: {
                                        marginLeft: 5,
                                        marginRight: 5,
                                        marginTop: 65,
                                        marginBottom: 25,
                                         colorsRanges: [
                                            [0,39, 'Gradient(white:grey)'],
                                            [40,59, 'Gradient(white:green)'],
                                            [60,69, 'Gradient(white:yellow)'],
                                            [70,100, 'Gradient(white:blue)']
                                            ],
                                        textSize : 5,
                                        border: false,
                                        needleHeadLength: 15,
                                        needleHeadWidth:0.04,
                                        title: \'''' + _("Humidity") + ''' %',
                                        titleSize: 10,
                                        titleBold: true
                                    }
                                }).grow().responsive([{maxWidth: 800,width:140,height:140,
                                                       options:{marginLeft:3,
                                                                marginRight: 3,
                                                                marginTop: 45,
                                                                marginBottom: 15,
                                                                titleSize: 5,
                                                                textSize : 4}},
                                                      {maxWidth: null,width:200,height:200,
                                                       options:{marginLeft:5,
                                                                marginRight: 5,
                                                                marginTop: 65,
                                                                marginBottom: 25,
                                                                textSize : 5}}]);
                            </script>
                            <canvas id="cvs4" width="190" height="190" style="float: left;">
                                [No canvas support]
                            </canvas>
                            <script>
                                my4 = new RGraph.Odometer({
                                    id: 'cvs4',
                                    min: 0,
                                    max: 2000,
                                    value: ''' + str(odometer) + ''',
                                    options: {
                                        border: false,
                                        colorsGreenMax: 800,                                        
                                        colorsRedMin: 1500,
                                        marginLeft: 5,
                                        marginRight: 5,
                                        marginTop: 20,
                                        marginBottom: 5,
                                        textSize : 7,
                                        title:\'''' + _("Air quality") + '''',
                                        titleSize: 9,
                                        titleBold: true
                                    }
                                }).grow().responsive([{maxWidth: 800,width:140,height:140,
                                                       options:{marginLeft:3,
                                                                marginRight: 3,
                                                                marginTop: 15,
                                                                marginBottom: 3,
                                                                titleSize: 5,
                                                                textSize : 4}},
                                                      {maxWidth: null,width:190,height:190,
                                                       options:{marginLeft:5,
                                                                marginRight: 5,
                                                                marginTop: 20,
                                                                marginBottom: 5,
                                                                textSize : 7}}]);
                            </script>
                            <canvas id="cvs5" width="190" height="190" style="float: left;">
                                [No canvas support]
                            </canvas>
                            <script>
                                my5 = new RGraph.Fuel({
                                    id: 'cvs5',
                                    min: 0,
                                    max: 100,
                                    value: ''' + str(fuel) + ''',
                                    options: {
                                        labelsEmpty: \'''' + _("Quiet") + '''',
                                        labelsFull: \'''' + _("Noisy") + '''',
                                        icon: '',
                                        scaleVisible: false,
                                        marginLeft: 5,
                                        marginRight: 5,
                                        marginTop: 15,
                                        marginBottom: 35,
                                        textSize : 7
                                    }
                                }).grow().responsive([{maxWidth: 800,width:140,height:140,
                                                       options:{marginLeft:3,
                                                                marginRight: 3,
                                                                marginTop: 10,
                                                                marginBottom: 25,
                                                                titleSize: 5,
                                                                textSize : 4}},
                                                      {maxWidth: null,width:190,height:190,
                                                       options:{marginLeft:5,
                                                                marginRight: 5,
                                                                marginTop: 15,
                                                                marginBottom: 35,
                                                                textSize : 7}}]);
                            </script>
                            <canvas id="cvs3" width="70" height="200" style="float: left;">
                                [No canvas support]
                            </canvas>
                            <script>
                                my3 = new RGraph.VProgress({
                                    id: 'cvs3',
                                    min: 0,
                                    max: 1000,
                                    value: ''' + str(progress) + ''',
                                    options: {
                                        colors: ['Gradient(#bbb:yellow)'],
                                        titleSide: "Lux",
                                        titleSideBold: true,
                                        scaleVisible: true,
                                        marginLeft: 25,
                                        marginRight: 25,
                                        marginTop: 25,
                                        marginBottom: 25,
                                        textSize : 7
                                    }
                                }).grow().responsive([{maxWidth: 800,width:20,height:80,
                                                       options:{marginLeft:5,
                                                                marginRight: 5,
                                                                marginTop: 5,
                                                                marginBottom: 5,
                                                                textSize : 5}},
                                                      {maxWidth: null,width:70,height:200,
                                                       options:{marginLeft:25,
                                                                marginRight: 25,
                                                                marginTop: 25,
                                                                marginBottom: 25,
                                                                textSize : 7}}]);
                            </script>

                            '''
    datafile += '''                        
                        </div>
                </div> 
                <div id="resultat" style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                background-color:#aaa; text-align: center;">
                </div>
                '''
    #
    # Main device options
    #
    if Devices[1].sValue == 'On' and 'RM2' in Parameters['Mode3']:
        rpath = str(Parameters["Mode2"]) + "remote/" + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + \
                "-" + str('{:03d}'.format(1)) + ".ini"
        datafile += '''
                <a id="econtrol">
                <button type="button" class="ui-button ui-corner-all"
                 title ="''' + _("Generate .ini files from e-Control database") + '''">e-Control</button>
                </a>
                <a id="import">
                <button type="button" class="ui-button ui-corner-all"
                 title ="''' + _('Import .ini files from the _import_ directory') + '''">
                 ''' + _("Import") + '''</button>
                </a>
                <a class="media-mobile popup" href="''' + url_edit + '''&amp;file=''' + rpath + '''" 
                    target="adminframe">
                    <button type="button" class="ui-button ui-corner-all" 
                    title = "''' + _("Edit ini file for remote controller") + '''">Remote INI</button>
                </a>

                <a class="media-mobile popup" href="''' + url_ircode + '''" target="_blank">
                    <button type="button" class="ui-button ui-corner-all"
                    title ="''' + _('Infra-red codes database') + '''">''' + _("IR code DB") + '''</button>
                </a>
                <a class="media-mobile"
                    onclick="$('#pronto').toggle(500)" >
                    <button type="button" class="ui-button ui-corner-all"
                    title ="''' + _('Create Broadlink code from Pronto HEX') + '''">
                    ''' + _("Create from Pronto") + '''</button>
                </a>
                <div id="pronto" style="display:none;">
                    <form id="BROpronto" method="POST" 
                            target="adminframe" action="''' + url_post + '''&amp;id='BROpronto'" 
                            enctype="application/x-www-form-urlencoded" 
                            onsubmit="return confirm(\'''' + msgconfirm + '''\');" name="BROpronto">
                        <textarea onClick="this.select();" id="fpronto" name="fpronto"                        
                            style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                            background-color:#fdf7f7;width:49%;">''' + _("Copy Past here 'Pronto HEX' code") + '''
                        </textarea>                                                
                        <input class="myButton" type="submit" value="''' + _('create') + '''" style="cursor: pointer;">
                    </form>
                </div>
                '''
    if refresh:
        if Parameters['Mode3'] == 'A1' or Parameters['Mode3'] == 'SP3S':
            datafile += _('Next refresh in') + ''': <span id='countdown'></span>
                                        <!-- JavaScript part -->
                                <script type="text/javascript">                                    
                                    // Total seconds to wait
                                    var seconds = ''' + str(sec) + ''';                                    
                                    function countdown() {                                        
                                        if (seconds < 0) {
                                            // Change your redirection link here
                                            window.location = "http://''' + Parameters['Address'] + ':' + \
                                                Parameters['Mode5'] + '/' + url + '''?key=''' + URLKEY + '''";
                                        } else {
                                            // Update remaining seconds
                                            document.getElementById("countdown").innerHTML = seconds;
                                            // Count down using javascript
                                            window.setTimeout("countdown()", 1000);
                                        }
                                        seconds = seconds - 1;
                                    }                                    
                                    // Run countdown function
                                    countdown();                                    
                                </script>
                                '''
    datafile += '''<hr>
            </div> '''

    #
    # loop ini files
    #
    if myini and 'RM2' in Parameters['Mode3']:
        for items in myini:
            mpath = str(Parameters["Mode2"]) + items
            config = configparser.ConfigParser()
            config.read(mpath, encoding='utf8')
            unitn = config.get("DEFAULT", "unit")
            pluginname = config.get("DEFAULT", "pluginname")
            hardwareid = config.get("DEFAULT", "hardwareid")
            learnedcode = config.get("LearnedCode", str(unitn))
            if 'ini=' in learnedcode:
                color = 'black'
            elif learnedcode[0:2] == 'b2' or learnedcode[0:2] == 'b1':
                color = 'purple'
            elif learnedcode[0:2] == 'd7':
                color = 'fuchsia'

            else:

                color = 'orange'

            customname = config.get("DEFAULT", "customname")
            if not customname:
                customname = "***"
            if int(unitn) in Devices:
                domunit = str(Devices[int(unitn)].ID)

            else:

                domunit = "***"

            url_dome = 'http://' + Parameters['Address'] + ':' + Parameters['Port'] + '/#/Devices/' + str(domunit) + \
                       '/LightEdit'
            url_del = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/delIni?key=' + URLKEY + \
                      '&amp;file=' + mpath + '&amp;plugunit=' + str(unitn)

            datafile += '''
                  <h3 style="color:''' + color + ''';" title ="''' + customname + '''">
                  ''' + ntpath.basename(mpath) + " -- " + domunit + '''</h3>
                  <div>
                        <span style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5);background-color:#fff; text-align:center;"> 
                            ''' + _("Ini file content") + '''
                        </span>
                    <div class="row">
                    <div class="column">
                        <ul>
                            <li>Domoticz Name : ''' + customname + '''</li> 
                            <li>Unit          : ''' + unitn + '''</li>                        
                            <li class="media-mobile">Plugin Name   : ''' + pluginname + '''</li>
                            <li class="media-mobile">HWID          : ''' + hardwareid + '''</li>                            
                            <li class="media-mobile">Domoticz IDX  : ''' + domunit + ''''''
            if domunit != '***':
                datafile += '''<a class="popup" href ="''' + url_dome + '''" title="Go">
                                <span style="cursor: pointer;background-color:#aaa;">&#8635;</span>
                                </a>'''
            datafile += '''
                            </li>
                        </ul> 
                    </div>
                    <div> 
                        <hr>
                        <a class="popup" href="''' + url_edit + '''&amp;file=''' + mpath + '''" target="adminframe">
                            <button type="button" class="ui-button ui-corner-all"
                            title = "''' + _('Edit ini file. Caution, no verification will be made') + '''"
                            >''' + _("Edit") + '''</button>
                        </a>
                        <a onclick="if(confirm(\'''' + msgconfirmu + '''\'))
                        {window.open(this.href,this.target)};return false;" href="''' + url_del + \
                        '''" target="adminframe">
                            <button type="button" class="ui-button ui-corner-all"
                            title = "''' + _('Delete ini file and related Domoticz device') + '''"
                            >''' + _("Delete") + '''</button>
                        </a>
                        '''
            if domunit == "***":
                datafile += '''
                        <a onclick="window.open(this.href,this.target);return false;" href="''' + url_cred + \
                            '''&amp;iunit=''' + unitn + '''&amp;icustom=''' + customname + '''" target="adminframe">
                          <button type="button" class="ui-button ui-corner-all"
                          title = "''' + _('Create Domoticz device linked to the ini file') + '''"
                          >''' + _("Create device") + '''</button>
                        </a>
                         '''
            devfile = Parameters['HomeFolder'] + "log/" + str(Parameters['HardwareID']) + Parameters['Mode3'] + ".txt"
            cmdfile = Parameters['HomeFolder'] + "broadlink_cli.py"
            if "ini=" not in learnedcode:
                cmd_code = 'python "' + cmdfile + '" --device "@' + devfile + '" --send "' + learnedcode + '"'

            else:

                cmd_code = 'curl "' + url_send + '''&amp;ini=''' + items + '"'

            datafile += '''
                        <hr>
                        <a class="media-mobile" onclick="$('#u''' + unitn + '''').toggle(500);" title="http link">
                            <span style="cursor: pointer;background-color:#aaa;">&#127760;</span>
                        </a>
                        <a class="media-mobile" onclick="$('#c''' + unitn + '''').toggle(500);" title="cmd link">
                            <span style="cursor: pointer;background-color:#aaa;">&lt;&#9839;&gt;</span>
                        </a>
                        <div id="u''' + unitn + '''" style="display:none;">
                        <textarea onClick="this.select();" 
                        style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                        background-color:#fdf7f7;width:49%;">''' + url_send + '''&amp;ini=''' + items + \
                        '''</textarea>
                        </div>                        
                        <div id="c''' + unitn + '''" style="display:none;">
                        <textarea onClick="this.select();" 
                        style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                        background-color:#fdf7f7;width:49%;">''' + cmd_code + '''</textarea>
                        </div>                        
                    </div>                    
                  </div>
                    <a class="media-mobile"
                        onclick="$('#t''' + unitn + '''').toggle(500);">
                        <button id="b''' + unitn + '''" 
                            type="button" class="ui-button ui-corner-all">''' + _("show code") + '''</button>
                    </a>'''
            if Devices[1].sValue == 'On':
                datafile += '''
                    <a onclick="$('#d''' + unitn + '''').dialog({
                                                                show:'slide',
                                                                position:{ my: 'top', at: 'top', of: event }});
                        $.post('sendCode?key=''' + URLKEY + '''&amp;ini=''' + items + '''');">
                        <button type="button" class="ui-button ui-corner-all">''' + _("send code") + '''</button>
                    </a>
                    '''
            if color != 'black':
                datafile += '''
                    <a onclick="$('#m''' + unitn + '''').toggle(500);">
                       <button type="button" class="ui-button ui-corner-all"
                        title ="''' + _('Number of time you want that the code be repeated') + '''">
                        ''' + _("modify repetition") + '''</button>
                    </a>'''
            datafile += '''
                    <div id="t''' + unitn + '''" style="display:none;">
                    <textarea  onClick="this.select();"
                    style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                    background-color:#fdf7f7; width:30%;">''' + learnedcode + '''</textarea>
                    </div>
                    <div id="d''' + unitn + '''" style="display:none;">''' + _("Code sent from unit :") + str(unitn) + \
                        '''<hr><span style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                        background-color:#aaa; text-align:center;" >
                        ''' + url_send + '''&amp;ini=''' + items + '''</span>                        
                        <a onclick="$.post('sendCode?key=''' + URLKEY + '''&amp;ini=''' + items + '''');" title="Go">
                        <span style="cursor: pointer;background-color:#aaa;">&#8635;</span>
                        </a>                   
                    </div>
                    <div id="m''' + unitn + '''" style="display:none;">
                        <form id="BROrep''' + unitn + '''" method="POST" target="adminframe" 
                            action="''' + url_post + "&amp;id='updrepeat'" + '''" 
                            enctype="application/x-www-form-urlencoded" 
                            onsubmit="return confirm(\'''' + msgconfirm + '''\');">
                        <label style="background-color:whitesmoke">''' + _("Number of repeat :") + '''</label>
                        <input type="number" min="0" max="99" size="2" id="updrepeat''' + unitn + '''" 
                                name="updrepeat" required value="''' + str(repeat) + '''">
                        <input type="hidden" id="updfile''' + unitn + '''" name="inifile" value="''' + mpath + '''">
                        <input class="myButton" type="submit" value="''' + _('update') + '''" style="cursor: pointer;">
                        </form>
                    </div>                                     
                   '''
            if str(domunit) == str(unitn):
                datafile += '''
                            '''
            datafile += '''<hr>
                  </div> '''
    datafile += '''
                </div>
                <div id='scroll_to_top'>
                    <a title="Top">
                        <span style="cursor:pointer;background-color:rgba(255, 99, 5, 0.7);color:black;font-size:45px;">
                            &#8686;
                        </span>
                    </a>
                </div>
            </body>
        </html>
                        '''
    return datafile


#
# generate HTML for countdown
#
def countdown(url, sec):
    if not sec:
        sec = 20

    htmldata = '''<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>                        
        <link rel="icon" href="data:,"/>
'''
    if autoresize:
        htmldata += '''
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                    '''/web/js/iframeResizer.contentWindow.js"></script>
'''
    htmldata += '''
        <style>
              blink {
                animation: blinker 0.6s linear infinite;
                color: #1c87c9;
               }
              @keyframes blinker {  
                50% { opacity: 0; }
               }
               .blink-one {
                 animation: blinker-one 1s linear infinite;
               }
               @keyframes blinker-one {  
                 0% { opacity: 0; }
               }
               .blink-two {
                 animation: blinker-two 1.4s linear infinite;
               }
               @keyframes blinker-two {  
                 100% { opacity: 0; }
               }
        </style>
    </head>
    <body>
        <div style="text-align:center;">
            <h3><p class="blink-two" style="background: yellow">''' + \
                _("Background process running ... wait for few seconds") + '''</p>
            </h3>
            <div id="resultat" style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),
            inset 5px 5px 8px rgba(0,0,0,0.5);background-color:#aaa;" align="center">
                <h3>
                    <p style="background: white">''' + \
                _("Remaining time before --") + url + ''' : 
               <span id="countdown" style="background: red">''' + str(sec) + '''</span>
                ''' + _("seconds") + '''
                    </p>
                </h3>
            </div>
            <!-- JavaScript part -->
            <script type="text/javascript">                                    
                // Total seconds to wait
                var seconds = ''' + str(sec) + ''';                                    
                function countdown() {
                   if (seconds < 0) {
                    // Change your redirection link here
                    window.location = "http://''' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/' + url + \
                '''?key=''' + URLKEY + '''";
                    } else {
                        // Update remaining seconds
                        document.getElementById("countdown").innerHTML = seconds;
                        // Count down using javascript
                        window.setTimeout("countdown()", 1000);
                    }
                    seconds = seconds - 1;
                }                                    
                // Run countdown function
                countdown();                                    
            </script>                                                                      
        </div>
    </body>                      
</html> 
'''

    return htmldata


#
# HTML for Multi Code ini creation
#
def multi_code():
    import fnmatch
    myini = []
    msgconfirm = _('Are you sure ?')
    url_post = 'http://' + Parameters['Address'] + ':' + Parameters['Mode5'] + '/postupdDatas?key=' + URLKEY

    # read folder content, search for ini files
    if 'RM2' in Parameters['Mode3']:
        try:
            ilist = os.listdir(Parameters['Mode2'])
            inipath = "*" + str(Parameters["Key"]) + "-" + str(Parameters["HardwareID"]) + "-*.ini"
            for file in ilist:
                if fnmatch.fnmatch(file, inipath):
                    myini.append(file)

            myini.sort(key=lambda a: a.lower())

        except os.error:

            return '<span style="background-color:whitesmoke;">' + _("No permission to list directory") + '</span>'

    htmldata = '''<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <title>Broadlink Devices</title>
        <link rel="icon" href="data:,"/>            
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/css/ui-darkness/jquery-ui.min.css" rel = "stylesheet">
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/css/manage.css" rel = "stylesheet">
        <link href = "''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/css/multi.css" rel = "stylesheet">
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/jquery-3.4.1.min.js"></script>
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Port"] + \
               '''/js/jquery-ui.min.js"></script>
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
               '''/web/js/Sortable.min.js"></script>
'''
    if autoresize:
        htmldata += '''
        <script src="''' + "http://" + Parameters["Address"] + ":" + Parameters["Mode5"] + \
                    '''/web/js/iframeResizer.contentWindow.js"></script>
'''
    htmldata += '''
    </head>
    <body style="background-color:whitesmoke;">
        <script>
            $(document).ready(function(){
                $(document).tooltip();
            });        
        </script>

        <hr>
        <div id="multi-sort">
            <h3 style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5); background-color: #fff; color: black;
             text-align: center;">''' + _('Multi-code ini file creation') + '''</h3>                
            <div id="resultat" style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                background-color: #aaa; text-align: center;">
            </div>
            <span style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5); background-color: #fff; text-align: center;">
                Drag and drop
            </span>                
            <div id="multi" class="row" 
                style="box-shadow: 2px 2px 5px rgba(0,0,0,0.5),inset 5px 5px 8px rgba(0,0,0,0.5);
                background-color:#ccc;">                    
                <div id="sourcecode-left" class="list-group column" style="background-color:yellow;">
                ''' + _('Source available') + ''' 
'''
    #
    # loop ini files, exclude multi-code
    #
    if myini and 'RM2' in Parameters['Mode3']:
        for items in myini:
            mpath = str(Parameters["Mode2"]) + items
            config = configparser.ConfigParser()
            config.read(mpath, encoding='utf8')
            unitn = config.get("DEFAULT", "unit")
            learnedcode = config.get("LearnedCode", str(unitn))
            custom = config.get("DEFAULT", "customname")
            if 'ini=' not in learnedcode:
                htmldata += '''
                            <div class="list-group-item handle" 
                                style="border-radius: 10px;box-shadow: 5px 5px 10px rgba(0,0,0,0.5);text-align:center;"
                                title="''' + custom + '''">
                                <input type="hidden" id="''' + items + '''" name="ini" value="''' + items + '''">
                                ''' + items + '''
                            </div>
'''
    htmldata += '''
            </div>                                        
                <form id="Cremulti" method="POST" target="adminframe" action="''' + url_post + '''&amp;id='Cremulti'"
                        enctype="application/x-www-form-urlencoded" 
                        onsubmit="return confirm(\'''' + msgconfirm + '''\');" name="Cremulti">                            
                    <div id="target-right" class="list-group column" style="background-color:grey;text-align:center;"
                        title = "''' + _('Drop ini file you want to include') + '''">                    
                      ''' + _('Include this sequence') + '''<hr>
                    </div>                    
                        <input class="ui-button" type="submit" value="''' + _('Create ini') + '''" 
                            style="cursor: pointer;" title="''' + _('Submit ini file creation') + '''">
                </form>                    
                <div id="timer-right" class="column" style="background-color:goldenrod;">
                    <hr>''' + _('Timer') + '''
                    <div class="list-group-item timer">
                    ''' + _('Add 1 second') + '''
                        <input type="hidden" id="timer" name="timer" value="1">
                    </div>                        
                </div>                                     
            </div>
        </div> 
        <script>
            var sourcecode = document.getElementById('sourcecode-left'),
            targetcode = document.getElementById('target-right'),
            timer = document.getElementById('timer-right');
            new Sortable(sourcecode, {
                group: 'shared', // set both lists to same group
                ghostClass: 'blue-background-class',
                handle: '.handle, .timer',
                animation: 350
                });
            new Sortable(targetcode, {
                group: 'shared',
                ghostClass: 'blue-background-class',
                animation: 350
                });
            new Sortable(timer, {
                group: {
                    name: 'shared',
                    pull: 'clone',
                    put: false // Do not allow items to be put into this list
                    },
                animation: 350,
                handle: '.timer',
                sort: false // To disable sorting: set sort to false
                });
        </script>
    </body>
</html>
'''
    return htmldata


#
# read controller.js and replace rid=0 by Domoticz Idx
#
def setcontrollerto(idx):

    ctrl = ''
    fn = Parameters["HomeFolder"] + "web/js/plugincontroller.js"
    try:
        with open(fn, 'r') as f:
            ctrl = f.read()
            ctrl = ctrl.replace('rid=0', 'rid=' + str(idx))

    except (ValueError, Exception):
        Domoticz.Error(traceback.format_exc())
        Domoticz.Error(_('File not exist or problem to access : {}').format(str(fn)))

    return ctrl


#
# Create Custom HTML for Angular
#
def displaydev(idx):

    htmldata = '''    
<!-- Placeholder for page content -->
<div id="plugin-view"></div>

<!-- Template for custom component -->
<script type="text/ng-template" id="app/myplugin/sampleComponent.html">
 <div class="container">
    <gz-back-to-top></gz-back-to-top>
    <div id="lightcontent"></div>
 </div>
</script>
<script>
    require(['app'], function(app) {
        // Custom component definition
        app.component('myPluginRoot', {
            templateUrl: 'app/myplugin/sampleComponent.html',
            controller: ''' + setcontrollerto(idx) + '''
        });

        // This piece triggers Angular to re-render page with custom components support
        angular.element(document).injector().invoke(function($compile) {
            var $div = angular.element('<my-plugin-root />');
            angular.element('#plugin-view').append($div);

            var scope = angular.element($div).scope();
            $compile($div)(scope);
        });
    });
</script>   
'''
    return htmldata


#
# Create Custom HTML device file
#
def customdev(idx):

    html_file = Parameters['StartupFolder'] + 'www/templates/Broadlink-' + Parameters['Mode3'] + '-' + \
        str(Parameters["HardwareID"]) + '-' + idx + '.html'

    if os.path.exists(html_file):

        return

    devfile = displaydev(idx)

    if os.path.isdir(Parameters['StartupFolder'] + 'www/templates/'):
        try:
            with open(html_file, 'w', encoding='utf-8') as fp:
                fp.write(devfile)
            Domoticz.Log(_('Device html file created: {}').format(html_file))

        except (ValueError, Exception):
            Domoticz.Error(traceback.format_exc())
            Domoticz.Error(_('Error to create device html file : {}').format(html_file))

    else:

        Domoticz.Error(_('Error to found www/templates for html file : {}').format(html_file))

    return

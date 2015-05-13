#!/usr/bin/env python

import os, sys, time
import subprocess
import fcntl
import requests

from Phidgets.PhidgetException import *
from Phidgets.Events.Events import *
from Phidgets.Devices.InterfaceKit import *

debug = False

board_list = {
    # Phidget: 4-port, shelf 6
    '4460panda-es' : ('phidget', 0, 0),
    '4430panda' : ('phidget', 0, 1),
    '3730xm' : ('phidget', 0, 2),
    '3530beagle' : ('phidget', 0, 3),

    # Phidget: 4-port, shelf 6
    'am335xbone' : ('phidget', 1, 0, 'off', 4, 'on'),
    'am335xboneb' : ('phidget', 1, 1, 'off', 4, 'on'),
    'omap5uevm' : ('phidget', 1, 2, 'off', 4, 'on'),
    'capri' : ('phidget', 1, 3),
    
    # Phidget: 4-port, shelf 6
    '3530overo' : ('phidget', 6, 0),
    '3730storm' : ('phidget', 6, 1),
    'am43xevm' : ('phidget', 6, 2),
    'rpi' : ('phidget', 6, 3),
#    'rpi' : ('acme', 0, 1),

    # Phidget: 8-port, shelf 2
    'sama5d3' : ('phidget', 2, 0),
    'xplained' : ('phidget', 2, 1),
    'mirabox': ('phidget', 2, 2),
    'st-b2120': ('phidget', 2, 3),
    'cubietruck': ('phidget', 2, 4),
    # free
    # free
    # free
    
    # Phidget: 8-port, shelf 4
    'cubie2' :('phidget', 3, 0),
    'armadillo' :('phidget', 3, 1),
#    'acme': ('phidget-', 3, 2), 
    'hikey': ('phidget-', 3, 2, 'off', 5, 'on'), 
    'cubie': ('phidget', 3, 3), 
    'dragon-usb' :('phidget', 3, 4),
    'arndale': ('phidget', 3, 5),
    'octa': ('phidget', 3, 6, 'off', 1, 'on'),
    'odroid-xu' :('phidget', 3, 7),

    # Phidget: 4-port, shelf 8
    'da850evm': ('phidget', 4, 0),
    'dm365evm': ('phidget', 4, 1, 'off', 4, 'on'),
    #'efm32': ('phidget', 4, 3, 'off', 1, 'on', 1, 'off', 1, 'on'),  # button pusher
    #'efm32': ('phidget', 4, 3, 'on', 1, 'off'),
    'chromebook2': ('phidget', 4, 2, 'off', 1, 'on'), # just grounds the reset line
    'jetson-button': ('phidget', 4, 3, 'on', 1, 'off'),

    # Phidget: shelf 10
    'kzm9d': ('phidget', 5, 0),
    'wand-quad': ('phidget', 5, 1),
    'wand-solo': ('phidget', 5, 2),
    'wand-dual': ('phidget', 5, 3),
    'ifc6410': ('phidget', 5, 4),
    'odroid-xu3': ('phidget', 5, 5, 'off', 4, 'on'),  # delay needed when HDMI cable plugged in.  Back power?
    'snowball': ('phidget', 5, 6),
    'bananapi': ('phidget', 5, 7),

    # SainSmart: 16-port
    'alpine': ("sain", "192.168.1.4", 1),  # 12 V
    'ifc6540': ("sain", "192.168.1.4", 2, 'off', 4, 'on'), # 12 V
    'sama5d4': ("sain", "192.168.1.4", 15), # 5V
    'mt8173evb': ("sain", "192.168.1.4", 16), # 5V

    # IP 9258 (power1), shelf 1
    'zynq' : ('ip9258', 1, 1), # 12 V
    'beaver' : ('ip9258', 1, 2),  # 12 V
    # free
    'obsax3' : ('ip9258', 1, 4), # 12 V
    
    # IP 9258 (power2), shelf 3
    'jetson': ('ip9258', 2, 1),  # 12 V
    'rk3288-evb' : ('ip9258', 2, 2, 'off', 10, 'on'), # 12 V
    'dragon': ('ip9258', 2, 3), # 'off', 10, 'on'),  # 12 V
    'cm-qs600': ('ip9258', 2, 4, 'off', 10, 'on'), # 12V

    # n900
    'n900': ('n900-', 0),

    # Sony phones
    'z1': ("sony", 0),

    # X10
    'light': ('x10-', 'a', 1),
    'heat': ('x10-', 'a', 7),


    # old
#    '335xbone' : ('power2', 1),
#    '335xbone' : ('power2', 1, 'off', 1, 'on'),
#    'osk' : ('power1', 3, 'off', 4, 'on'),
#    '37xxevm' : ('power2', 2),
}

class phidget:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.serial_numbers = (262305, # 4-port, shelf 6
                               262295, # 4-port, shelf 6
                               318471, # 8-port, shelf 2
                               312226, # 8-port, shelf 4
                               259764, # 4-port, shelf 8
                               319749, # 8-port, shelf 10
                               259763, # 4-port, shelf 6
                               )
        self.serial_num = self.serial_numbers[id]
        self.lockfile = "/var/run/lock/phidget-%s.lock" %self.id
        self.lock_fp = open(self.lockfile, "w")
        self.lock_fd = self.lock_fp.fileno()
        fcntl.lockf(self.lock_fd, fcntl.LOCK_EX)
        if debug:
            print "[%.2f] Aquired lock for Phidget %s" %(time.time(), self.id)

        try:
            self.device = InterfaceKit()	
        except RuntimeError as e:
            print("Runtime Error: %s" % e.message)
    
        try:
            self.device.openPhidget(serial=self.serial_num)
        except PhidgetException as e:
            print ("Phidget Exception %i: %s" % (e.code, e.detail))
            fcntl.lockf(self.lock_fd, fcntl.LOCK_UN)
            exit(1)

        self.device.waitForAttach(10000)

        #print ("Phidget %d attached!" % (self.device.getSerialNum()))
        #print ("Phidget has %d inputs, %d outputs, %d sensors"
        #       %(self.device.getInputCount(), self.device.getOutputCount(), self.device.getSensorCount()))

    def close(self):
        self.device.closePhidget()
        fcntl.lockf(self.lock_fd, fcntl.LOCK_UN)
        if debug:
            print "[%.2f] Released lock for Phidget %s" %(time.time(), self.id)

    def on(self):
        self.device.setOutputState(self.port, 1)

    def off(self):
        self.device.setOutputState(self.port, 0)

    def cmd(self, cmd):
        if cmd == 'on':
            self.on()
        if cmd == 'off':
            self.off()


class br:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.dev = '/dev/ttyS0'
        self.cmd_base = 'br -x %s' %(self.dev)

    def send(self, val):
        cmd = self.cmd_base + ' %c%d %s' %(self.id, self.port, val)
        os.system(cmd)

    def on(self):
        self.send('on')

    def off(self):
        self.send('off')

    def cmd(self, cmd):
        self.send(cmd)

    def close(self):
        pass

class ip9258:
    def __init__(self, id, port):
        self.id = id
        self.name = 'power%d' %id
        self.port = port
        self.power_oid = '1.3.6.1.4.1.92.58.2.%d.0' %(self.port)
        self.cmd_base = 'snmpset -v 1 -c public %s %s integer' \
            %(self.name, self.power_oid)

    def close(self):
        pass

    def send(self, val):
        cmd = self.cmd_base + ' %d > /dev/null' %(val)
        os.system(cmd)

    def on(self):
        self.send(1)

    def off(self):
        self.send(0)

    def cmd(self, cmd):
        if cmd == 'on':
            self.on()
        elif cmd == 'off':
            self.off()

class acme:
    def __init__(self, id, probe):
        self.acme_id = id
        self.probe_id = probe
        
    def close(self):
        pass

    def cmd(self, cmd):
        sigrok_cmd = "ssh root@192.168.1.108 sigrok-cli --driver=acme --config probes=%d" %self.probe_id
        if cmd == 'on':
            sigrok_cmd += ":poweron=1"
        elif cmd == 'off':
            sigrok_cmd += ":poweroff=1"
        sigrok_cmd += " --set"
        sigrok_cmd += " > /dev/null 2>&1"
        subprocess.call(sigrok_cmd, shell=True)

class sain:
    def __init__(self, ip, relay):
        self.ip = ip
        self.relay = relay
        self.url_base = "http://%s/30000/" %self.ip

    def close(self):
        pass

    def cmd(self, cmd):
        val = (self.relay - 1) * 2
        if cmd == "on":
            val += 1
        url = self.url_base + "%02d" %val
        requests.get(url)

class n900:
    def __init__(self):
        self.tools_dir = "/home/khilman/work.local/platforms/nokia/rover"
    
    def close(self):
        pass

    def cmd(self, cmd):
        subprocess.call("cd %s; ./%s" %(self.tools_dir, cmd), shell=True)

class sony:
    def close(self):
        pass

    def on(self):
        self.tty = open("/home/khilman/dev/z1-1", "w")  # UART control IF
        # ensure power off
        self.tty.write("pvabc");
        time.sleep(0.2)
        # power on into fastboot mode
        self.tty.write("PB") # VBAT, press volume up
        time.sleep(0.5)
        self.tty.write("V")  # apply VBUS
        time.sleep(1)
        self.tty.write("b")  # release volume-up key
        self.tty.close()
        
    def off(self):
        self.tty = open("/home/khilman/dev/z1-1", "w")  # UART control IF
        self.tty.write("pvabc")
        self.tty.close()
        
    def cmd(self, cmd):
        if cmd == 'on':
            self.on()
        elif cmd == 'off':
            self.off()

def main():
    args = sys.argv[1:]
    if '--' in args:
        i = args.index('--')
        boards = args[0:i]
        force_cmds = args[i+1:]
    else:
        boards = args
        force_cmds = ''

    for b in boards:
        b = b.strip()
        for k, v in board_list.iteritems():
            num = v[1]
            if b == 'all' or k == b:
                type = v[0]

                # magic flags on 'type'
                flag = type[-1]
                if flag == '-':
                    type = type[:-1]  # drop the magic flag

                    # '-' : don't include in 'all'
                    if b == 'all':
                        print "Ignore:", k, "due to '%c' flag: " %flag
                        continue

                if debug:
                    print "Reboot:", k, ";", type,
                    if len(v) >= 2:
                        print v[1],
                    if len(v) >= 3:
                        print v[2],
                    print ": ",

                if type == 'phidget':
                    board = phidget(v[1], v[2])
                elif type == 'x10':
                    board = br(v[1], v[2])
                elif type == 'ip9258':
                    board = ip9258(v[1], v[2])
                elif type == 'n900':
                    board = n900()
                elif type == 'sony':
                    board = sony()
                elif type == "acme":
                    board = acme(v[1], v[2])
                elif type == "sain":
                    board = sain(v[1], v[2])
                else:
                    print "Type", type, "not recognized.  Giving up."
                    sys.exit(1)

                if force_cmds != '':
                    cmds = force_cmds
                else:
                    cmds = v[3:]

                # if commands, assume 'off', sleep, 'on'
                if len(cmds) == 0:
                    if debug:
                        print "off, sleep, on"
                    board.cmd("off")
                    time.sleep(2)
                    board.cmd("on")
                else:
                    if debug:
                        print cmds
                    for cmd in cmds:
                        try:
                            sleep = int(cmd)
                        except:
                            # not a number
                            sleep = -1

                        if sleep > 0:
                            time.sleep(sleep)
                        else:
                            board.cmd(cmd.strip())

                board.close()

if __name__ == "__main__":
    main()

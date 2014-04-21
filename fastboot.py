#!/usr/bin/env python
#
# fastboot helper for conmux (also support Nokia OMAP Loader a.k.a NOLO)
#
import os
import sys
import tempfile
import tftpy
import subprocess
import time

tftp_server = '192.168.1.2'

def usage():
    print "Usage: fastboot <board> <tftp kernel path> [tftp dtb path] [tftp initrd path]"

if len(sys.argv) < 2:
    usage()
    sys.exit(1)

board = sys.argv[1]
args = sys.argv[2:]
kernel = args[0]
dtb = None
initrd = None
if len(args) > 1:
    dtb = args[1]
if len(args) > 2:
    initrd = args[2]
    if initrd == 'None':
        initrd = None

print sys.argv
print sys.argv[0], board, kernel, dtb, initrd

boards = {
    'dragon': ("25001b4", "boot", "console=ttyMSM0,115200,n8 debug earlyprintk"),
    'capri': ("1234567890", "flash", ""),
#    'n900': (None, "nolo", "console=ttyO2,115200n8 debug"),
    'n900': (None, "nolo", "init=/sbin/preinit ubi.mtd=rootfs root=ubi0:rootfs rootfstype=ubifs rootflags=bulk_read,no_chk_data_crc rw console=ttyMTD,log console=tty0 console=ttyO2,115200n8 debug init=/bin/sh"),
}

kernel_l = ''
dtb_l = ''
initrd_l = ''
bootimg = ''
def cleanup():
    if os.path.exists(kernel_l):
        print "Deleting", kernel_l
        os.unlink(kernel_l)
    if os.path.exists(dtb_l):
        print "Deleting", dtb_l
        os.unlink(dtb_l)
    if os.path.exists(initrd_l):
        print "Deleting", initrd_l
        os.unlink(initrd_l)
    if os.path.exists(bootimg):
        print "Deleting", bootimg
        os.unlink(bootimg)
    sys.exit(0)

id = None
if boards.has_key(board):
    id = boards[board][0]
    fastboot_cmd = boards[board][1]
    cmdline = boards[board][2]
else:
    print "Unknown board %s.  Giving up." %board
    cleanup()

try:
    client = tftpy.TftpClient(tftp_server, 69)

    fd, kernel_l = tempfile.mkstemp(prefix='kernel-')
    print 'TFTP: download kernel (%s) to %s' %(kernel, kernel_l)
    client.download(kernel, kernel_l, timeout=60)

    if dtb:
        fd, dtb_l = tempfile.mkstemp(prefix='dtb-')
        print 'TFTP: download dtb (%s) to %s' %(dtb, dtb_l)
        client.download(dtb, dtb_l)

    if initrd:
        fd, initrd_l = tempfile.mkstemp(prefix='initrd-')
        print 'TFTP: download initrd (%s) to %s' %(initrd, initrd_l)
        client.download(initrd, initrd_l)

except tftpy.TftpShared.TftpException as e:
    print("Error {0}".format(str(e)))
    cleanup()

if fastboot_cmd == 'boot':
    # fastboot requires DTB appended
    cmd = "cat %s >> %s" %(dtb_l, kernel_l)
    subprocess.call(cmd, shell=True)

    cmd = 'fastboot -s %s -c "%s" boot %s %s' %(id, cmdline, kernel_l, initrd_l)
    print cmd
    subprocess.call(cmd, shell=True)

elif fastboot_cmd == 'flash':
    cmd = 'fastboot -s %s flash kernel %s' %(id, kernel_l)
    subprocess.call(cmd, shell=True)
    cmd = 'fastboot -s %s flash device-tree %s' %(id, dtb_l)
    subprocess.call(cmd, shell=True)
    cmd = 'fastboot -s %s flash initrd %s' %(id, initrd_l)
    subprocess.call(cmd, shell=True)
    cmd = 'fastboot -s %s -c "%s" continue' %(id, cmdline)
    subprocess.call(cmd, shell=True)

# Nokia NOLO commands
elif fastboot_cmd == 'nolo':
    flasher_cmd = "/home/khilman/work.local/platforms/nokia/rover/flasher"
    cmd = "%s -l -k %s " %(flasher_cmd, kernel_l)
    if initrd_l:
        cmd += "-n %s " %initrd_l
    cmd += "-b"
    if cmdline:
        cmd += '"%s" ' %cmdline
    subprocess.call(cmd, shell=True)

cleanup()


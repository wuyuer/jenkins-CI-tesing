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
import getopt

tftp_server = '192.168.1.2'

def usage():
    print "Usage: fastboot <board> <tftp kernel path> [tftp dtb path] [tftp initrd path]"

if len(sys.argv) < 2:
    usage()
    sys.exit(1)

board = sys.argv[1]

try:
    opts,args =  opts, args = getopt.getopt(sys.argv[2:], "t:")
except getopt.GetoptError as err:
    print str(err) # will print something like "option -a not recognized"
    sys.exit(2)
for o, a in opts:
    if o == "-t":
        tftp_server = a

#args = sys.argv[2:]
kernel = args[0]
dtb = None
initrd = None
if len(args) > 1:
    dtb = args[1]
    if dtb == 'None':
        dtb = None
if len(args) > 2:
    initrd = args[2]
    if initrd == 'None':
        initrd = None

print "Running:", " ".join(sys.argv)

boards = {
    'dragon': ("25001b4", "boot", None),
    'ifc6410': ("153952c", "boot", None),
    'ifc6540': ("105869a1", "boot", None),
    'capri': ("1234567890", "flash", ""),
    'n900': (None, "nolo", None),
    'z1': ("BH9006CT08", "sony", None),
    'rk3288-evb': (None, "rockchip", None),
    'cm-qs600': ("f0b93ea2", "boot", None),
}

kernel_l = ''
dtb_l = ''
initrd_l = ''
bootimg = ''
def cleanup():
    if os.path.exists(kernel_l):
        os.unlink(kernel_l)
    if os.path.exists(dtb_l):
        os.unlink(dtb_l)
    if os.path.exists(initrd_l):
        os.unlink(initrd_l)
    if os.path.exists(bootimg):
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
        fd, dtb_l = tempfile.mkstemp(prefix='dtb-', suffix=".dtb")
        print 'TFTP: download dtb (%s) to %s' %(dtb, dtb_l)
        client.download(dtb, dtb_l)

        # Check if DTB has command-line
        try:
            dtb_cmdline = subprocess.check_output("fdtget %s /chosen bootargs" %dtb_l, shell=True).strip()
            print "INFO: Using commandline from DTB: ", dtb_cmdline
            if dtb_cmdline:
                cmdline = dtb_cmdline
        except subprocess.CalledProcessError:
            # fdtget returned non-zero
            pass

    if initrd:
        fd, initrd_l = tempfile.mkstemp(prefix='initrd-')
        print 'TFTP: download initrd (%s) to %s' %(initrd, initrd_l)
        client.download(initrd, initrd_l)

except tftpy.TftpShared.TftpException as e:
    print("Error {0}".format(str(e)))
    cleanup()

if fastboot_cmd == 'boot':
    fastboot_args = ""

    # qcom hackery
    if board.startswith("ifc6") or board.startswith("cm-qs"):
        fastboot_args = "-b 0x82000000"
        fd, kernel_fixup = tempfile.mkstemp(prefix='kernel-fixup-')
        cmd = "cat /home/khilman/work.local/platforms/qcom/ifc6410/fixup.bin %s > %s" %(kernel_l, kernel_fixup)
        print "INFO:", cmd
        subprocess.call(cmd, shell=True)
        os.remove(kernel_l)
        kernel_l = kernel_fixup

    # fastboot requires DTB appended
    cmd = "cat %s >> %s" %(dtb_l, kernel_l)
    print "INFO:", cmd
    subprocess.call(cmd, shell=True)

    cmd = "fastboot -s %s " %id
    cmd += "boot %s " %fastboot_args
    if cmdline:
        cmd += '-c "%s" ' %cmdline 

    cmd += "%s %s" %(kernel_l, initrd_l)
    print cmd
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    print output

elif fastboot_cmd == 'flash':
    cmd = 'fastboot -s %s flash kernel %s' %(id, kernel_l)
    subprocess.call(cmd, shell=True)
    if dtb_l:
        cmd = 'fastboot -s %s flash device-tree %s' %(id, dtb_l)
        subprocess.call(cmd, shell=True)
    if initrd_l:
        cmd = 'fastboot -s %s flash initrd %s' %(id, initrd_l)
        subprocess.call(cmd, shell=True)
    cmd = 'fastboot -s %s -c "%s" continue' %(id, cmdline)
    subprocess.call(cmd, shell=True)

# Nokia NOLO commands
elif fastboot_cmd == 'nolo':
    # NOLO requires DTB appended
    cmd = "cat %s >> %s" %(dtb_l, kernel_l)
    subprocess.call(cmd, shell=True)

    nokia_tools = "/home/khilman/work.local/platforms/nokia/rover"
    os.chdir(nokia_tools)
    cmd = "./off; sleep 1; ./on; ./flasher -l -k %s " %kernel_l
#    if initrd_l:
#        cmd += "-n %s " %initrd_l
    cmd += "-b"
    if cmdline:
        cmd += '"%s" ' %cmdline
    print cmd
    subprocess.call(cmd, shell=True)

elif fastboot_cmd == "sony":
    dtb_tmpdir = tempfile.mkdtemp()
    fd, dtb_qcom = tempfile.mkstemp(dir=dtb_tmpdir, prefix="qcom-", suffix=".dtb")

    # Insert qcom,msm-id is in the DTS
    print "INFO: Inserting qcom,msm-id into DTB"
    fd, dts_tmp = tempfile.mkstemp(suffix=".dts")
    qcom_frag = "/ { qcom,msm-id = <126 8 0>, <185 8 0>, <186 8 0>; };"
    cmd = "dtc -I dtb -O dts -o %s %s" %(dts_tmp, dtb_l)
    subprocess.call(cmd, shell=True)
    fp = open(dts_tmp, "a")
    fp.write(qcom_frag)
    fp.close()
    cmd = "dtc -I dts -O dtb -o %s %s" %(dtb_qcom, dts_tmp)
    subprocess.call(cmd, shell=True)
    os.unlink(dts_tmp)

    fd, bootimg = tempfile.mkstemp(prefix="boot.img")
    mkbootimg_args = "--base 0x00000000 --pagesize 2048 --ramdisk_offset 0x02000000 --tags_offset 0x01e00000 "
    cmd = "/usr/local/bin/mkqcdtbootimg %s --output %s --kernel %s " %(mkbootimg_args, bootimg, kernel_l)
    if initrd_l:
        cmd += "--ramdisk %s " %initrd_l
    if cmdline:
	cmd += '--cmdline "%s" ' %cmdline
    if dtb_l:
#        cmd += "--dt_dir %s " %os.path.dirname(dtb_l)
        cmd += "--dt_dir %s " %os.path.dirname(dtb_qcom)
    print cmd
    subprocess.call(cmd, shell=True)

#    subprocess.call("hexdump -C %s | head -20" %bootimg, shell=True)
    bootimg_size = os.path.getsize(bootimg)
    if bootimg_size <= 0:
        print "ERROR: boot.img size is %d.  Giving up." %bootimg_size

    cmd = "fastboot -s %s erase boot" %id
    print "INFO: Erasing boot partition:", cmd
    subprocess.call(cmd, shell=True)

    cmd = "fastboot -s %s flash boot %s" %(id, bootimg)
    print "INFO: Flashing boot partition:", cmd
    subprocess.call(cmd, shell=True)

    print "INFO: Rebooting"
    tty = open("/home/khilman/dev/z1-1", "w")
    tty.write("pvabc")
    time.sleep(0.5)
    tty.write("P")
    time.sleep(0.5)
    tty.write("A")
    time.sleep(1)
    tty.write("a")
    tty.close()

    shutil.rmtree(dtb_tmpdir)

elif fastboot_cmd == "rockchip":
    os.chdir("/home/khilman/work.local/platforms/rockchip")

    # requires DTB appended
    cmd = "cat %s >> %s" %(dtb_l, kernel_l)
    subprocess.call(cmd, shell=True)

    # erase kernel at beginning of eMMC
    cmd = "./bin/rkflashtool w 0x0 0x8000 < /dev/zero > /dev/null"
    subprocess.call(cmd, shell=True)

    # write kernel to beginning of eMMC
    cmd = "./bin/rkflashtool w 0x0 0x8000 < %s > /dev/null" %kernel_l
    subprocess.call(cmd, shell=True)

    # write initrd to eMMC
    if initrd_l:
        cmd = "./bin/rkflashtool w 0x10000 0x8000 < %s > /dev/null" %initrd_l
        subprocess.call(cmd, shell=True)

    # reboot (default u-boot env set to boot kernel from MMC)
    cmd = "./bin/rkflashtool b"
    subprocess.call(cmd, shell=True)


cleanup()


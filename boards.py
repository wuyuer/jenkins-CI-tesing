#!/usr/bin/env python

import os
import sys
import json
import types
import subprocess
import struct

cfg_dir = "/home/khilman/work/kernel/tools/build-scripts"
initrd_armel = "/opt/kjh/rootfs/buildroot/arm/rootfs.cpio.gz"
initrd_armeb = "/opt/kjh/rootfs/buildroot/armeb/rootfs.cpio.gz"
initrd_arm64 = "/opt/kjh/rootfs/buildroot/arm64/rootfs.cpio.gz"

initrd = None

def usage():
    print "Usage: %s <build dir>"

def zimage_is_big_endian(kimage):
    """Check zImage big-endian magic number"""
    magic_offset = 0x30
    setend_be = 0xf1010200
    setend_be_thumb = 0xb658

    fp = open(kimage, "r")
    fp.seek(magic_offset)
    val = struct.unpack("=L", fp.read(4))[0]
    fp.seek(magic_offset)
    val16 = struct.unpack("<H", fp.read(2))[0]
    fp.close()
    if (val == 0x01020304) or (val == setend_be):
        return True
    return False

if len(sys.argv) < 2:
    usage()
    sys.exit(1)

boards_json = os.path.join(cfg_dir, "boards.json")
fp = open(boards_json, "r")
boards = json.load(fp)
fp.close()

dir = os.path.abspath(sys.argv[1])
base = os.path.dirname(dir)
cwd = os.getcwd()

builds = os.listdir(dir)

boot_count = 0
total_count = 0
for board in boards.keys():
    a = 0
    c = 0
    b = boards[board]
    if b.has_key("disabled") and b["disabled"]:
        continue

    arch = "arm"
    if b.has_key("arch"):
        arch = b["arch"]

    dtbs = []
    if b.has_key("dtb"):
        d = b["dtb"]
        if d:
            if type(d) is types.ListType:
                dtbs = d
            else:
                dtbs = [d]
    else:
        dtbs = [board]

    if b.has_key("legacy"):
        dtbs.append(None)
    
    console = board
    if b.has_key("console"):
        console = b["console"]

    # add extra defconfigs based on flags
    if b.has_key("defconfig"):
        defconfig_list = list(b["defconfig"])  # make a copy before appending
        extra = None
        if b.has_key("LPAE") and b["LPAE"]:
            for defconfig in defconfig_list:
                b["defconfig"].append(defconfig + "+" + "CONFIG_ARM_LPAE=y")
        if b.has_key("endian") and b["endian"] == "both":
            for defconfig in defconfig_list:
                b["defconfig"].append(defconfig + "+" + "CONFIG_CPU_BIG_ENDIAN=y")

    if b.has_key("defconfig"):
        for defconfig in b["defconfig"]:
            d = "%s-%s" %(arch, defconfig)
            for build in builds:
                if build != d:
                    continue;

                os.chdir(os.path.join(dir, build))

                kimage = "zImage"
                if arch == "arm64":
                    kimage = "Image"
                if not os.path.exists(kimage):
                    print "WARNING: kernel doesn't exist:", build, kimage
#                    continue

                initrd = initrd_armel
                if zimage_is_big_endian(kimage):
                    initrd = initrd_armeb
                if arch == "arm64":
                    initrd = initrd_arm64

                for dtb in dtbs:
                    if dtb:
                        dtb_path = os.path.join("dtbs", dtb) + ".dtb"
                        if not os.path.exists(dtb_path):
#                            print "WARNING: DTB doesn't exist:", dtb_path
                            continue

                    # dtb == None means legacy boot, but only allow for non multi* defconfigs
                    elif defconfig.startswith("multi"):
                        continue
                    else:
                        dtb_path = "-"

                    if dtb == None:  # Legacy
                        #logname = "LEGACY_%s" %board
                        #logname = "legacy,%s" %board
                        logname = "legacy,%s" %console
                    else:
                        logname = board

                    a += 1
                    total_count += 1
                    logbase = "boot-%s" %logname
                    logfile = logbase + ".log"
                    jsonfile = logbase + ".json"
                    if os.path.exists(jsonfile):
                        fp = open(jsonfile)
                        boot_json = json.load(fp)
                        fp.close()
                        if boot_json["boot_result"] == "PASS":
                            print "\t%s/%s: Boot JSON reports PASS.  Skipping." %(board, d)
                            continue

#                    print "\t", console, d, dtb_path
                    cmd = "pyboot -s -l %s %s %s %s %s" %(logfile, console, kimage, dtb_path, initrd)
                    print "\t", d, cmd
                    subprocess.call(cmd, shell=True)
                    c += 1

    print "%d / %d\t%s" %(c, a, board)
    boot_count += c
#    break


print "-------\n%d / %d" %(boot_count, total_count)



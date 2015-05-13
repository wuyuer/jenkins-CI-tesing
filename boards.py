#!/usr/bin/env python
#

import os
import sys
import json
import types
import subprocess
import struct
import fileinput
import re
import operator
import itertools
# to install run `pip install futures` on Python <3.2
from concurrent.futures import ThreadPoolExecutor as Pool

cfg_dir = "/home/khilman/work/kernel/tools/build-scripts"
initrd_armel = "/opt/kjh/rootfs/buildroot/armel/rootfs.cpio.gz"
initrd_armeb = "/opt/kjh/rootfs/buildroot/armeb/rootfs.cpio.gz"
initrd_arm64 = "/opt/kjh/rootfs/buildroot/arm64/rootfs.cpio.gz"
lab = "lab-khilman"

initrd = None

subprocs = []
max_subprocs = 20

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
tree = os.path.basename(os.getcwd())

builds = os.listdir(dir)

mach_dict = {}
board_count = 0
boot_count = 0
total_count = 0
pool = Pool(max_workers=max_subprocs)

# keep track of blacklist, to be removed on the fly
blacklist = {}
if os.path.exists('.blacklist'):
    for line in fileinput.input('.blacklist'):
        if line.startswith('#') or len(line) <= 1:
            continue
        ver_pat, defconfig, dtb = line.split()
        m = re.search(ver_pat, os.path.basename(dir))
        if not m:
            continue
        if not blacklist.has_key(defconfig):
            blacklist[defconfig] = list()
        if dtb == "legacy" or dtb == "None":
            dtb = "legacy"
        blacklist[defconfig].append(dtb)

for board in boards.keys():
    a = 0
    c = 0
    b = boards[board]
    if b.has_key("disabled") and b["disabled"]:
        continue

    arch = b.get("arch", "arm")
    mach = b.get("mach", None)
    k = "%s-%s" %(arch, mach)
    mach_dict[k] = mach_dict.get(k, 0) + 1
    if mach == None:
        print "WARNING: board", board, "has no mach type."

    dtbs = []
    if b.has_key("dtb"):
        d = b["dtb"]
        if d:
            if type(d) is types.ListType:
                dtbs = d
            else:
                dtbs = [d]
    
    # on arm64, use mach type is dir for finding dtb
    elif arch == "arm64" and mach:
        dtbs = [os.path.join(mach, board)]

    else:
        dtbs = [board]

    if b.has_key("legacy"):
        dtbs.append(None)
    
    console = board
    if b.has_key("console"):
        console = b["console"]

    modules = b.get("modules", "modules.tar.xz")
    modules = None

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
        if "multi_v7_defconfig" in defconfig_list:
            b["defconfig"].append("multi_v7_defconfig+CONFIG_PROVE_LOCKING=y")
#            b["defconfig"].append("multi_v7_defconfig+tiny")

    if not b.has_key("rootfs"):
        b["rootfs"] = ["ramdisk", ]

    if b.has_key("defconfig"):
        for defconfig, rootfs in itertools.product(b["defconfig"], b["rootfs"]):
            d = "%s-%s" %(arch, defconfig)

            for build in builds:
                if build != d:
                    continue;

                run_dir = os.path.join(dir, build)
                os.chdir(run_dir)
                build_json = os.path.join("build.json")

                try:
                    fp = open(build_json, "r")
                except IOError as e:
                    print "ERROR: Could not open %s " %os.path.join(run_dir, build_json),
                    print "I/O error({0}): {1}".format(e.errno, e.strerror)

                build_meta = json.load(fp)
                fp.close()

                git_describe = build_meta.get("git_describe", None)
                git_commit = build_meta.get("git_commit", None)
                git_branch = build_meta.get("git_branch", None)
                git_url = build_meta.get("git_url", None)
                
                if not os.path.exists(lab):
                    os.mkdir(lab)

                kimage = "zImage"
                if arch == "arm64":
                    kimage = "Image"
                if rootfs == "ramdisk" and os.path.exists(kimage):
                    initrd = initrd_armel
                    if zimage_is_big_endian(kimage):
                        initrd = initrd_armeb
                    if arch == "arm64":
                        initrd = initrd_arm64
                else:
                    initrd = ""

                if modules and not os.path.exists(modules):
                    modules = None

                for dtb in dtbs:
                    blacklisted = False
                    if dtb:
                        dtb_path = os.path.join("dtbs", dtb) + ".dtb"
                        if not os.path.exists(dtb_path):
#                            print "WARNING: DTB doesn't exist:", dtb_path, ". Skipping."
                            continue

                    # dtb == None means legacy boot, but only allow for non multi* defconfigs
                    elif defconfig.startswith("multi"):
                        continue
                    else:
                        dtb_path = "-"

                    # check blacklist
                    for key in blacklist.keys():
                        if d.startswith(key):
                            if dtb and (dtb in blacklist[key]):
                                blacklisted = True
                            elif board in blacklist[key]:
                                blacklisted = True
                    if blacklisted:
                        print "\tSkipping %s/%s.  Blacklisted." %(dtb, d)
                        continue
                        
                    if dtb == None:  # Legacy
                        logname = "%s,legacy" %board                        
                    else:
                        logname = board

                    # Hack: to distinguish between rootfs types, append to board "name"
                    if rootfs != "ramdisk":
                        logname += "_rootfs:%s" %rootfs
                    
                    a += 1
                    total_count += 1
                    logbase = "boot-%s" %logname
                    logbase = os.path.join(lab, logbase)

                    logfile = logbase + ".txt"
                    jsonfile = logbase + ".json"
                    if os.path.exists(jsonfile):
                        fp = open(jsonfile)
                        boot_json = json.load(fp)
                        fp.close()
                        if boot_json["boot_result"] == "PASS":
                            print "\t%s/%s: Boot JSON reports PASS.  Skipping." %(board, d)
                            continue

                    build_result = build_meta.get("build_result", "UNKNOWN")
                    job = build_meta.get("job", None)
                    if build_result != "PASS":
                        print "\t%s%s: WARNING: Build failed.  Creating %s" %(board, d, jsonfile)
                        boot_json = {"boot_result": "UNTRIED"}
                        boot_json["boot_result_description"] = "Kernel build failed."
                        boot_json["version"] = "1.0"
                        boot_json["board"] = logname
                        boot_json["lab_name"] = lab
                        boot_json["arch"] = arch
                        boot_json["defconfig"] = defconfig
                        boot_json["kernel"] = git_describe
                        if job:
                            boot_json["job"] = job

                        fp = open(jsonfile, "w")
                        json.dump(boot_json, fp, indent=4, sort_keys=True)
                    else:
                        cmd = "pyboot -q -b %s -w -s -n %s -L %s -l %s" %(build_json, logname, lab, logfile)
                        if mach:
                            cmd += " -M %s" %mach
                        if modules:
                            cmd += " -m %s" %modules
                        cmd += " %s %s %s %s" %(console, kimage, dtb_path, initrd)
                        print "\t", d, cmd
                        f = pool.submit(subprocess.call, "(cd %s; %s)" %(run_dir, cmd), shell=True)

                    c += 1

    print "%d / %d\t%s" %(c, a, board)
    boot_count += c
    board_count += 1


print "-------\n%d / %d Boots." %(boot_count, total_count)
print board_count, "Boards."
print len(mach_dict), "Mach types."
#sorted_mach = sorted(mach_dict.items(), key=operator.itemgetter(1), reverse=True)
#for val in sorted_mach:
#    print "%2d: %s" %(val[1], val[0])

# Wait for any remaining jobs to finish
pool.shutdown()



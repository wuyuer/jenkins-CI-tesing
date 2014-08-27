#!/usr/bin/env python
#
# TODO: implement blacklist in board-map
#
import os, sys, glob, re
import subprocess, fileinput
import struct

skip_existing_logs = True
dry_run = False

boot_defconfigs = {
    'arm-bcm_defconfig': (),
    'arm-davinci_all_defconfig': (),
    'arm-exynos_defconfig': (),
    'arm-imx_v6_v7_defconfig': (),
    'arm-qcom_defconfig': (),
    'arm-multi_v7_defconfig+CONFIG_ARM_LPAE=y': ('sun7i-a20-cubieboard2.dtb', 'omap5-uevm.dtb', 'armada-xp-openblocks-ax3-4.dtb', 'tegra124-jetson-tk1.dtb', 'exynos5250-arndale.dtb', 'exynos5410-smdk5410.dtb', 'exynos5420-arndale-octa.dtb', 'exynos5800-peach-pi.dtb', 'vexpress-v2p-ca15-tc1.dtb', ),
    'arm-multi_v7_defconfig+CONFIG_CPU_BIG_ENDIAN=y': ('armada-xp-openblocks-ax3-4.dtb', 'armada-370-mirabox.dtb',),
    'arm-multi_v7_defconfig': (),
    'arm-mvebu_defconfig': (),
    'arm-mvebu_v7_defconfig': (),
    'arm-mvebu_v7_defconfig+CONFIG_CPU_BIG_ENDIAN=y': ('armada-xp-openblocks-ax3-4.dtb', 'armada-370-mirabox.dtb', ),
    'arm-omap2plus_defconfig': (),
    'arm-sama5_defconfig': (),
    'arm-sunxi_defconfig': (),
    'arm-tegra_defconfig': (),
    'arm-u8500_defconfig': (),
    'arm-shmobile_defconfig': (),
    'arm-vexpress_defconfig': (),
    'arm64-defconfig': (),
}

board_map = {
    # OMAP
    'am335x-bone.dtb': ('am335xbone', ),
    'am335x-boneblack.dtb': ('am335xboneb', ),
    'omap3-beagle.dtb': ('3530beagle', ),
    'omap3-beagle-xm.dtb': ('3730xm', ),
#    'omap3-tobi.dtb': ('3530overo', '3730storm'),
    'omap3-tobi.dtb': ('3530overo', ),
    'omap3-overo-tobi.dtb': ('3530overo', ),
    'omap3-overo-storm-tobi.dtb': ('3730storm', ),
    'omap3-n900.dtb': ('n900', ),
    'omap4-panda.dtb': ('4430panda', ),
    'omap4-panda-es.dtb': ('4460panda-es', ),
    'omap5-uevm.dtb': ('omap5uevm', ),

    # Exynos
    'exynos5250-arndale.dtb': ('arndale', ),
    'exynos5420-arndale-octa.dtb': ('octa', ),
    'exynos5410-odroidxu.dtb': ('odroid-xu', ),
    'exynos5410-smdk5410.dtb': ('odroid-xu', ),
    'exynos5800-peach-pi.dtb': ('chromebook2', ),

    # sunxi
    'sun4i-a10-cubieboard.dtb': ('cubie', ),
    'sun7i-a20-cubieboard2.dtb': ('cubie2', ),

    # i.MX
    'imx6dl-wandboard.dtb': ('wand-solo', 'wand-dual', ),
    'imx6q-wandboard.dtb': ('wand-quad', ),

    # atmel
    'sama5d35ek.dtb': ('sama5', ),

    # Marvell
    'armada-370-mirabox.dtb': ('mirabox', ),
    'armada-xp-openblocks-ax3-4.dtb': ('obsax3', ),

    # Tegra
    'tegra30-beaver.dtb': ('beaver', ),
    'tegra124-jetson-tk1.dtb': ('jetson', ),

    # u8500
    'ste-snowball.dtb': ('snowball', ),

    # Broadcom
    'bcm28155-ap.dtb': ('capri', ),

    # Qcom
    'qcom-apq8074-dragonboard.dtb': ('dragon', ),

    # Davinci
    'da850-evm.dtb': ('da850evm', ),

    # shmobile
    'emev2-kzm9d.dtb': ('kzm9d', ),

    # ARM
    'vexpress-v2p-ca15-tc1.dtb': ('vexpress-v2p-ca15', ),
    'vexpress-v2p-ca9.dtb': ('vexpress-v2p-ca9', ),

    # Xilinx
    'zynq-zc702.dtb': ('zynq', ),
    }

legacy_map = {
    'arm-da8xx_omapl_defconfig': ('da850evm', ), 
    'arm-davinci_all_defconfig': ('dm365evm', ),
    'arm-omap2plus_defconfig': ('3530beagle', '3730xm', '3530overo', '3730storm', 'n900', ),
    'arm-versatile_defconfig': ('versatilepb', ),
    'arm-vexpress_defconfig': ('vexpress-v2p-ca9', ),
    'arm64-defconfig': ('qemu-aarch64', ),
}

dir = os.path.abspath(sys.argv[1])
base = os.path.dirname(dir)
cwd = os.getcwd()
retval = 0

def new_zimage_is_big_endian(kimage):
    """Check zImage big-endian magic number"""
    magic_offset = 0x30
    fp = open(kimage, "r")
    fp.seek(magic_offset)
    val = struct.unpack("=L", fp.read(4))[0]
    fp.close()
    if (val == 0x01020304):
        return True
    return False

def zimage_is_big_endian(kimage):
    """Check zImage for 'setend be' instruction just after magic headers."""
    setend_offset = 0x30
    setend_be = 0xf1010200
    setend_be_thumb = 0xb658
    fp = open(kimage, "r")
    fp.seek(setend_offset)
    instr = struct.unpack("<L", fp.read(4))[0]
    fp.seek(setend_offset)
    instr_thumb = struct.unpack("<H", fp.read(2))[0]
    fp.close()
    if (instr == setend_be) or (instr_thumb == setend_be_thumb):
        return True
    return False

def boot_boards(zImage, dtb, boards):
    if dtb:
        dtb_l = os.path.join(dtb_base, dtb)
        d, ext = os.path.splitext(dtb)
    else:
        dtb_l = '-'
        d = 'legacy'

    for board in boards:
        print
        print "Boot: %s,%s on board %s" %(build, dtb, board)

        if len(boards) > 1 or dtb == None:
            logfile = "boot-%s,%s.log" %(d, board)
        else:
            logfile = "boot-%s.log" %d
        base, ext = os.path.splitext(logfile)
        if skip_existing_logs:
            json = base + ".json"
            if os.path.exists(json):
                print "Skipping %s.  JSON file exists: %s\n" %(board, json)
                continue

        if not os.path.exists(zImage):
            print "Skipping %s.  kernel doesn't exist: %s\n" %(board, json)
            continue

        # Check endianness of zImage
        endian = "little"
        initrd = ""
        if new_zimage_is_big_endian(zImage) or zimage_is_big_endian(zImage):
            endian = "big"
            initrd = "/opt/kjh/rootfs/buildroot/armeb/rootfs.cpio.gz"

        cmd = 'pyboot -w -s -l %s %s %s %s %s' \
              %(logfile, board, zImage, dtb_l, initrd)

        if board.startswith('LAVA'):
            cmd = 'lboot %s %s' %(zImage, dtb_l)
        if dry_run:
            print cmd
        else:
            r = subprocess.call(cmd, shell=True)
            if r != 0:
                retval = 1

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Unbuffer output

# Add items from whitelist directly to board_map
if os.path.exists('.whitelist'):
    for line in fileinput.input('.whitelist'):
        if line.startswith('#'):
            continue
        dtb, board = line.split()
        print "Adding", dtb, "to board_map for", board
        board_map[dtb] = (board, )

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
        blacklist[defconfig].append(dtb)

for build in os.listdir(dir):
    path = os.path.join(dir, build)

    if not os.path.isdir(path):
        continue

    arch = 'arm'
    defconfig = build
    if '-' in build:
        (arch, defconfig) = build.split('-', 1)

    if not (build in boot_defconfigs.keys() or build in legacy_map.keys()):
        continue

    zImage = 'zImage'
    if arch == 'arm64':
        zImage = 'Image'

    dtb_base = 'dtbs'
    if os.path.exists(os.path.join(path, 'arch/%s/boot' %arch)):
        zImage = os.path.join('arch/%s/boot', 'zImage' %arch)
        dtb_base = 'arch/%s/boot/dts' %arch

    #
    # Legacy boot
    #
    if legacy_map.has_key(build):
        boards = legacy_map[build]
        os.chdir(path)
        boot_boards(zImage, None, boards)
        os.chdir(cwd)

    # 
    # DT boot
    #
    if not boot_defconfigs.has_key(build):
        continue

    dtb_list = boot_defconfigs[build]
    for dtb_path in glob.glob('%s/%s/*.dtb' %(path, dtb_base)):
        dtb = os.path.basename(dtb_path)

        # if dtb_list is not empty, only try defconfigs in list
        if dtb_list:
            if not dtb in dtb_list:
                continue

        if not board_map.has_key(dtb):
            continue

        i = defconfig.find('+')
        if i > 0:
            d = defconfig[:i]
        else:
            d = defconfig
        if blacklist.has_key(d) and dtb in blacklist[d]:
            print "Blacklisted: ", defconfig, dtb
            continue

        boards = board_map[dtb]
        os.chdir(path)
        boot_boards(zImage, dtb, boards)
        os.chdir(cwd)

sys.exit(retval)

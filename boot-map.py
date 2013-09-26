#!/usr/bin/env python

import os, sys, glob
import subprocess

boot_defconfigs = (
    'omap2plus_defconfig',
    'exynos_defconfig',
    'multi_v7_defconfig',
    'imx_v6_v7_defconfig',
    'sama5_defconfig',
    'mvebu_defconfig',
)

board_map = {
    # OMAP
    'am335x-bone.dtb': ('am335xbone', ),
    'am335x-boneblack.dtb': ('am335xboneb', ),
    'omap3-beagle.dtb': ('3530beagle', ),
    'omap3-beagle-xm.dtb': ('3730xm', ),
    'omap3-tobi.dtb': ('3530overo', '3730storm'),
    'omap4-panda.dtb': ('4430panda', ),
    'omap4-panda-es.dtb': ('4460panda-es', ),

    # Exynos
    'exynos5250-arndale.dtb': ('arndale', ),

    # sunxi
    'sun4i-a10-cubieboard.dtb': ('cubie', ),
    
    # i.MX
    'imx6dl-wandboard.dtb': ('wand-solo', 'wand-dual', ),
    'imx6q-wandboard.dtb': ('wand-quad', ),

    # atmel
    'sama5d35ek.dtb': ('sama5', ),

    # Marvell
    'armada-370-mirabox.dtb': ('mirabox', ),
    }

dir = os.path.abspath(sys.argv[1])
base = os.path.dirname(dir)
cwd = os.getcwd()
retval = 0
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Unbuffer output
for build in os.listdir(dir):
    if '-' in build:
        (arch, defconfig) = build.split('-', 1)

    if not defconfig in boot_defconfigs:
        continue

    path = os.path.join(dir, build)
    for dtb_path in glob.glob('%s/arch/arm/boot/dts/*.dtb' %path):
        dtb = os.path.basename(dtb_path)

        if not board_map.has_key(dtb):
            continue

        boards = board_map[dtb]
        zImage = os.path.join('arch/arm/boot', 'zImage')
        dtb_l = os.path.join('arch/arm/boot/dts', dtb)
        d, ext = os.path.splitext(dtb)
        os.chdir(path)
        for board in boards:
            print
            print "Boot: %s,%s on board %s" %(build, dtb, board)
            if len(boards) > 1:
                logfile = "boot-%s,%s.log" %(d, board)
            else:
                logfile = "boot-%s.log" %d
            cmd = 'pyboot -s -l %s %s %s %s' \
                %(logfile, board, zImage, dtb_l)
            r = subprocess.call(cmd, shell=True)
            if r != 0:
                retval = 1

        os.chdir(cwd)

sys.exit(retval)

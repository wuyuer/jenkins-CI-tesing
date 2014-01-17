#!/usr/bin/env python
#
# TODO: implement blacklist in board-map
#
import os, sys, glob
import subprocess

boot_defconfigs = {
    'bcm_defconfig': (),
    'exynos_defconfig': (),
    'imx_v6_v7_defconfig': (),
#    'msm_defconfig': (),
    'multi_lpae_defconfig': ('sun7i-a20-cubieboard2.dtb', ),
    'multi_v7_defconfig': (),
    'mvebu_defconfig': (),
    'omap2plus_defconfig': (),
    'sama5_defconfig': (),
    'sunxi_defconfig': (),
    'tegra_defconfig': (),
    'u8500_defconfig': (),
}

board_map = {
    # OMAP
    'am335x-bone.dtb': ('am335xbone', ),
    'am335x-boneblack.dtb': ('am335xboneb', ),
#    'omap3-beagle.dtb': ('3530beagle', ),
    'omap3-beagle-xm.dtb': ('3730xm', ),
    'omap3-tobi.dtb': ('3530overo', '3730storm'),
    'omap4-panda.dtb': ('4430panda', ),
    'omap4-panda-es.dtb': ('4460panda-es', ),

    # Exynos
    'exynos5250-arndale.dtb': ('arndale', ),

    # sunxi
#    'sun4i-a10-cubieboard.dtb': ('cubie', ),
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

    # u8500
    'ste-snowball.dtb': ('snowball', ),

    # Broadcom
    'bcm28155-ap.dtb': ('LAVA:capri', ),

    # Qcom
#    'qcom-apq8074-dragonboard.dts': ('dragon', ),
    }

dir = os.path.abspath(sys.argv[1])
base = os.path.dirname(dir)
cwd = os.getcwd()
retval = 0

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Unbuffer output
for build in os.listdir(dir):
    path = os.path.join(dir, build)

    if not os.path.isdir(path):
        continue

    defconfig = build
    if '-' in build:
        (arch, defconfig) = build.split('-', 1)

    if not defconfig in boot_defconfigs.keys():
        continue
    
    zImage = 'zImage'
    dtb_base = 'dtbs'
    if os.path.exists(os.path.join(path, 'arch/arm/boot')):
        zImage = os.path.join('arch/arm/boot', 'zImage')
        dtb_base = 'arch/arm/boot/dts'

    dtb_list = boot_defconfigs[defconfig]
    for dtb_path in glob.glob('%s/%s/*.dtb' %(path, dtb_base)):
        dtb = os.path.basename(dtb_path)

        # if dtb_list is not empty, only try defcon
        if dtb_list:
            if not dtb in dtb_list:
                continue

        if not board_map.has_key(dtb):
            continue

        boards = board_map[dtb]
        dtb_l = os.path.join(dtb_base, dtb)

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
            if board.startswith('LAVA'):
                cmd = 'lboot %s %s zImage' %(zImage, dtb_l)
            r = subprocess.call(cmd, shell=True)
            if r != 0:
                retval = 1

        os.chdir(cwd)

sys.exit(retval)

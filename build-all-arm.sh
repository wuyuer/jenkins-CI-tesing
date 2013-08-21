#!/bin/bash

TOOLS=/work/kernel/tools

ARCH=arm
#DEFCONFIGS=$(cd arch/arm/configs; echo *_defconfig)
DEFCONFIGS=$(cd arch/arm/configs; echo *_defconfig)
DEFCONFIGS=omap2plus_defconfig

LOG="report-$(git describe).log"
exec > >(tee ${LOG})

# 
# Build
#
for defconfig in ${DEFCONFIGS}; do
    build.sh ${ARCH} ${defconfig}

    (cd build-$(git describe)/${ARCH}-${defconfig}; ${TOOLS}/boot/boot-tool.py ${defconfig})

done

#
# Boot
#
if [ -e ${TOOLS}/boot/boot-report.py ]; then
    for defconfig in ${DEFCONFIGS}; do
	(cd build-$(git describe)/${ARCH}-${defconfig}; \
	    ${TOOLS}/boot/boot-tool.py ${defconfig})
    done
fi

#
# Report
#
if [ -e ${TOOLS}/boot/boot-report.py ]; then
    ${TOOLS}/boot/boot-report.py build-$(git describe)
fi

${TOOLS}/build-scripts/build-report.py build-$(git describe)


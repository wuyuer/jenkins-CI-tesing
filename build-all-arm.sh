#!/bin/bash

TOOLS=/work/kernel/tools/build-scripts

ARCH=arm
DEFCONFIGS=$(cd arch/arm/configs; echo *_defconfig)
#NICE=nice

BUILD="build-$(git describe)"
LOG="${BUILD}.log"
exec > >(tee ${LOG})

# Build (per-defconfig builds under build-$(git describe)
date +%s > timestamp.start
for defconfig in ${DEFCONFIGS}; do
    ${NICE} build.sh --quiet ${ARCH} ${defconfig}
done
date +%s > timestamp.end

# Build report
if [ -e ${TOOLS}/build-report.py ]; then
  ${TOOLS}/build-report.py ${BUILD}
fi

# Boot
if [ -e ${TOOLS}/boot-map.py ]; then
   ${TOOLS}/boot-map.py ${BUILD}
fi 

# boot report
if [ -e ${TOOLS}/boot-report.py ]; then
   ${TOOLS}/boot-report.py ${BUILD}
fi 

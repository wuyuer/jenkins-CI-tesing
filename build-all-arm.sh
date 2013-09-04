#!/bin/bash

TOOLS=/work/kernel/tools/build-scripts
#MAIL="-m somone@somewhere.org"

ARCH=arm
DEFCONFIGS=$(cd arch/arm/configs; echo *_defconfig)
#NICE=nice
CCACHE=$(which ccache)
export CCACHE_DIR=${PWD}/.ccache

BUILD="build-$(git describe)"
LOG="${BUILD}.log"
exec > >(tee ${LOG})

if [[ ${CCACHE} ]]; then
    ccache --max-size=16G > /dev/null
    ccache --zero-stats > /dev/null
fi

# Build (per-defconfig builds under build-$(git describe)
date +%s > timestamp.start
for defconfig in ${DEFCONFIGS}; do
    ${NICE} build.sh --quiet ${ARCH} ${defconfig}
done
date +%s > timestamp.end

if [[ ${CCACHE} ]]; then
    ccache --show-stats
fi

# Build report
if [ -e ${TOOLS}/build-report.py ]; then
  ${TOOLS}/build-report.py ${MAIL} ${BUILD}
fi

# Boot
if [ -e ${TOOLS}/boot-map.py ]; then
   ${TOOLS}/boot-map.py ${BUILD}
fi 

# boot report
if [ -e ${TOOLS}/boot-report.py ]; then
   ${TOOLS}/boot-report.py ${MAIL} ${BUILD}
fi 

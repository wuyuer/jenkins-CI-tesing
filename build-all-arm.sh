#!/bin/bash

#MAILTO="-m somone@somewhere.org"

ARCH=arm
DEFCONFIGS=$(cd arch/arm/configs; echo *_defconfig)
#NICE=nice
CCACHE=$(which ccache)
export CCACHE_DIR=${PWD}/.ccache

BUILD="build-$(git describe)"
LOG="${BUILD}.log"
exec > >(tee ${LOG})
exec 2>&1

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
build-report.py ${MAILTO} ${BUILD}

# Boot
which pyboot
if [ $? == 0 ]; then
    # Boot test
    boot-map.py ${BUILD}
    # boot report
    boot-report.py ${MAILTO} ${BUILD}
fi

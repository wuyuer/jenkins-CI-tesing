#!/bin/bash

TOOLS_DIR=/work/kernel/tools/

# Command-line options
QUIET=0
while :; do
    case $1 in
	--quiet) QUIET=1; shift ;;
	*) break
    esac
done

ARCH=${1:-arm}
defconfig=${2:-defconfig}

if [[ -z ${CROSS_COMPILE} ]]; then
   . ${TOOLS_DIR}cross-env.sh $ARCH
fi

# Base options for make
MAKE_OPTS="ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE "
MAKE_OPTS+="KALLSYMS_EXTRA_PASS=1 CONFIG_DEBUG_SECTION_MISMATCH=y "
CPUS=`cat /proc/cpuinfo |grep ^processor |wc -l`
MAKE_THREADS=$[CPUS * 2]
MAKE_OPTS+="-k -j${MAKE_THREADS} "

# Output dir and build logs
DATE=`date +%Y%m%d.%H%M%S`
GIT_HASH=`git log -n1 --abbrev=8 --format=%h`
if [[ ${TMPDIR} ]]; then
  OUTPUT_BASE="${TMPDIR}/build-${GIT_HASH}"
else
  OUTPUT_BASE="build-${GIT_HASH}"
fi

OUTPUT_DIR="${OUTPUT_BASE}/${ARCH}-${defconfig}"
BUILD_LOG=${OUTPUT_BASE}/${ARCH}-${defconfig}-${DATE}.log
mkdir -p ${OUTPUT_DIR}
MAKE_OPTS+="O=${OUTPUT_DIR} "

CCACHE=`which ccache`
if [[ ${CCACHE} ]]; then
  MAKE_OPTS+="CC=\"ccache ${CROSS_COMPILE}gcc\" "
  export CCACHE_DIR=${OUTPUT_BASE}/ccache
fi

RESULT="PASS"

# Redirect stdout ( > ) into a named pipe ( >() ) running "tee"
touch ${BUILD_LOG}
if [ $QUIET -eq 1 ]; then
    echo "Build log: ${BUILD_LOG}"
    exec >> ${BUILD_LOG}
else
    exec > >(tee ${BUILD_LOG})
fi

# and stderr to stdout
exec 2>&1

echo
echo ARCH=${ARCH}
echo defconfig=${defconfig}
echo CROSS_COMPILE=${CROSS_COMPILE}
echo CCACHE=${CCACHE}
echo CCACHE_DIR=${CCACHE_DIR}
echo MAKE_OPTS=${MAKE_OPTS}
echo OUTPUT_DIR=${OUTPUT_DIR}
echo BUILD_LOG=${BUILD_LOG}
echo TMPDIR=${TMPDIR}
echo PWD=${PWD}
echo
echo

function do_report {
    if [[ ${CCACHE} ]]; then
       (set -x; ${CCACHE} --show-stats)
    fi

    # Clean up: if output is in tmpfs, delete it
    if [[ ${OUTPUT_DIR} = /run/shm/* ]]; then
       echo "Removing build output: ${OUTPUT_DIR}"
       /bin/rm -rf ${OUTPUT_DIR}
    fi

    END_TIME=`date +%s`
    BUILD_TIME=$(( $END_TIME - $START_TIME ))
    echo 
    echo "========================================================"
    echo "Build output: ${OUTPUT_DIR}"
    echo "Build log: ${BUILD_LOG}"
    echo "Result: ${ARCH}-${defconfig}: ${RESULT} # Build time: ${BUILD_TIME} seconds."
    echo

    echo ${ARCH}-${defconfig} >> ${OUTPUT_BASE}/${RESULT}

    if [ $QUIET -eq 1 ]; then
       echo "Result: ${ARCH}-${defconfig}: ${RESULT} # Build time: ${BUILD_TIME} seconds." > /dev/tty
    fi

    exit $1;
}

function do_make {
    (set -x; eval make ${MAKE_OPTS} $@)
    retval=$?
    if [ $retval != 0 ]; then
	RESULT="FAIL"
	do_report $retval
    fi

    return $retval
}

# Show compiler version
(set -x; ${CROSS_COMPILE}gcc --version)

if [[ ${CCACHE} ]]; then
   (set -x; ${CCACHE} --zero-stats)
fi

START_TIME=`date +%s`

# Configure
do_make ${defconfig}

# Build kernel
do_make
(set -x; ${CROSS_COMPILE}size ${OUTPUT_DIR}/vmlinux)

# Optionally build modules
if [ -e ${OUTPUT_DIR}/.config ]; then
    grep -q CONFIG_MODULES=y ${OUTPUT_DIR}/.config
    if [ $? = 0 ]; then
	do_make modules
    fi
fi

retval=0
if [ $RESULT = "FAIL" ]; then
    retval=1
fi

do_report $retval

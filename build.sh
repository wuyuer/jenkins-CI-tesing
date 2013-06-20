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
  OUTPUT_TOP="${TMPDIR}/build-${GIT_HASH}"
else
  OUTPUT_TOP="${PWD}/build-${GIT_HASH}"
fi

OUTPUT_BASE=${OUTPUT_TOP}/${ARCH}-${defconfig}
OUTPUT_DIR=${OUTPUT_BASE}/output
BUILD_LOG=${OUTPUT_BASE}/build.log
mkdir -p ${OUTPUT_DIR}
MAKE_OPTS+="O=${OUTPUT_DIR} "

if [[ -z ${CCACHE_DISABLE} ]]; then
  CCACHE=`which ccache`
fi
if [[ ${CCACHE} ]]; then
  MAKE_OPTS+="CC=\"ccache ${CROSS_COMPILE}gcc\" "
  if [[ -z ${CCACHE_DIR} ]]; then
     export CCACHE_DIR=${OUTPUT_TOP}/ccache
     mkdir -p ${CCACHE_DIR}
  fi
fi

RESULT="PASS"

# Redirect stdout ( > ) into a named pipe ( >() ) running "tee"
if [ $QUIET -eq 1 ]; then
    exec > ${BUILD_LOG}
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
    echo "Result: ${ARCH}-${defconfig}: ${RESULT} # Build time: ${BUILD_TIME} seconds."
    echo

    if [ $QUIET -eq 1 ]; then
	echo $ARCH-$defconfig $RESULT $BUILD_TIME | awk '{ printf "Result: %32s: %s # Build time: %4d sec\n", $1, $2, $3}' > /dev/tty
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
cp ${OUTPUT_DIR}/.config ${OUTPUT_BASE}/kernel.config

# Build kernel
if [ ${ARCH} = arm ]; then
    target="zImage dtbs"
fi

do_make ${target}

if [ ${ARCH} = arm ]; then
    (cd ${OUTPUT_DIR}; cp -a System.map arch/arm/boot/zImage ${OUTPUT_BASE})
    mkdir -p ${OUTPUT_BASE}/dts
    cp -a ${OUTPUT_DIR}/arch/arm/boot/dts/*.dtb ${OUTPUT_BASE}/dts
fi
    
(set -x; ${CROSS_COMPILE}size ${OUTPUT_DIR}/vmlinux)



# Optionally build modules
if [ -e ${OUTPUT_DIR}/.config ]; then
    grep -q CONFIG_MODULES=y ${OUTPUT_DIR}/.config
    if [ $? = 0 ]; then
	do_make modules

	export INSTALL_MOD_PATH=${OUTPUT_BASE}
	do_make modules_install
    fi
fi

retval=0
if [ $RESULT = "FAIL" ]; then
    retval=1
fi

do_report $retval

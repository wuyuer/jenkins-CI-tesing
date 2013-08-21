#!/bin/bash

LINK=`readlink $0`
if [[ ${LINK} ]]; then
  TOOLS_DIR=`dirname $LINK`
else
  TOOLS_DIR=`dirname $0`
fi

# Command-line options
QUIET=0
while :; do
    case $1 in
	--quiet) QUIET=1; shift ;;
	*) break
    esac
done

ARCH=${1:-arm}
defconfig_full=${2:-defconfig}

defconfig_simple=0
defconfig_prefix=$(dirname $defconfig_full)
if [ $defconfig_prefix == '.' ]; then 
    defconfig_prefix=''
    defconfig_simple=1
    defconfig=$(basename $defconfig_full)
else
    # Handle defconfig + fragments
    OIFS=${IFS}
    IFS='+'
    defconfig_frags=($defconfig_full)
    IFS=${OIFS}

    for frag in ${defconfig_frags[@]}; do
	combined+="$(basename $frag)+"
    done
    defconfig="${combined%?}"  # drop trailing ','
fi

if [[ -z ${CROSS_COMPILE} ]]; then
   . ${TOOLS_DIR}/cross-env.sh $ARCH
fi

# Base options for make
MAKE_OPTS="ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE "
MAKE_OPTS+="KALLSYMS_EXTRA_PASS=1 CONFIG_DEBUG_SECTION_MISMATCH=y "
CPUS=`cat /proc/cpuinfo |grep ^processor |wc -l`
MAKE_THREADS=$[CPUS * 2]
MAKE_OPTS+="-k -j${MAKE_THREADS} "

# Output dir and build logs
if [[ -z ${OUTPUT_PREFIX} ]]; then
  OUTPUT_PREFIX="build-"
fi
if [[ -z ${OUTPUT_TOP} ]]; then
  OUTPUT_TOP="${PWD}/${OUTPUT_PREFIX}$(git describe)"
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
     ${CCACHE} --max-size=16G > /dev/null
  fi
fi

RESULT="PASS"
WARN=0
SECT=0

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

    # Clean up: remove build output
    /bin/rm -rf ${OUTPUT_DIR}
    /bin/rm -f PASS FAIL
    touch ${OUTPUT_BASE}/${RESULT}

    END_TIME=`date +%s`
    BUILD_TIME=$(( $END_TIME - $START_TIME ))

    echo 
    echo "Result: ${ARCH}-${defconfig}: ${RESULT} # ${WARN} warnings, ${SECT} mismatches; Built in ${BUILD_TIME} sec"
    echo

    if [ $QUIET -eq 1 ]; then
	echo $ARCH-$defconfig $RESULT $WARN $SECT $BUILD_TIME | awk '{ printf "%32s: %s # %3s warnings, %2s mismatches, %4d sec\n", $1, $2, $3, $4, $5}' > /dev/tty
    fi

    exit $1;
}

function do_make {
    (set -x; eval make ${MAKE_OPTS} $*)
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
if [[ ${defconfig_simple} == 1 ]]; then
    do_make ${defconfig}
else
    (set -x; ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} ./scripts/kconfig/merge_config.sh -O ${OUTPUT_DIR} ${defconfig_frags[@]})
fi

cp ${OUTPUT_DIR}/.config ${OUTPUT_BASE}/kernel.config

# Build kernel
if [ ${ARCH} = arm ]; then
    target="zImage dtbs"
fi

do_make ${target}

if [ ${ARCH} = arm ]; then
    (cd ${OUTPUT_DIR}; cp -a System.map ${OUTPUT_BASE})
    mkdir -p ${OUTPUT_BASE}/arch/arm
    cp -r ${OUTPUT_DIR}/arch/arm/boot ${OUTPUT_BASE}/arch/arm
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

# Check warnings
WARN=`grep -i warning ${BUILD_LOG} | wc -l`
SECT=`grep -i "Section Mismatch" ${BUILD_LOG}| wc -l`

retval=0
if [ $RESULT = "FAIL" ]; then
    retval=1
fi

do_report $retval

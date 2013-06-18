#!/bin/bash
#
# Source this file to get correct ARCH= and CROSS_COMPILE= env
# for the various arches.
#
GCC_VER=4.6.3

declare -A tool
tool=(
[alpha]="alpha alpha-linux"
[arm]="arm arm-unknown-linux-gnueabi"
[arm64]="arm64 aarch64-linux-gnu /opt/local/gcc-linaro/bin/"
[blackfin]="blackfin bfin-uclinux"
[cris32]="cris crisv32-linux"
[cris64]="cris cris-linux"
[ia64]="ia64 ia64-linux"
[frv]="frv frv-linux"
[h8300]="h8300 h8300-elf"
[m68k]="m68k m68k-linux"
[mips32]="mips mips-linux"
[mips64]="mips mips64-linux"
[m32r]="m32r m32r-linux"
[hppa32]="parisc hppa-linux"
[hppa64]="parisc hppa64-linux"
[ppc32]="powerpc powerpc-linux"
[ppc64]="powerpc powerpc64-linux"
[s390]="s390 s390x-linux"
[sh]="sh sh4-linux"
[sparc32]="sparc sparc-linux"
[sparc64]="sparc sparc64-linux"
[xtensa]="xtensa xtensa-linux"
[i386]="i386"
[x86_64]="x86_64"
)

line=`echo ${tool[$1]}`
arch=`echo ${tool[$1]} | cut -d' ' -f1`
cross=`echo ${tool[$1]} | cut -s -d' ' -f2`
cross_path=`echo ${tool[$1]} | cut -s -d' ' -f3`

CROSS_COMPILE=
if [[ ${cross} ]]; then
  CROSS_PATH=${cross_path:="/opt/local/gcc-${GCC_VER}-nolibc/${cross}/bin/"}
  export CROSS_COMPILE=${CROSS_PATH}$cross-
fi

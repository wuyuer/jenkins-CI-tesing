#!/bin/bash

TOOLS=`dirname $0`

START=`date +%s`
COUNT=0

DEFCONFIGS=`(cd arch/arm/configs; echo *_defconfig)`
for defconfig in $DEFCONFIGS; do
  ${TOOLS}/build.sh --quiet arm ${defconfig}
  COUNT=$(( $COUNT + 1 ))
done

END=`date +%s`
BUILD_TIME=$(( $END - $START ))
MIN=$(( BUILD_TIME / 60 ))
SEC=$(( BUILD_TIME % 60 ))
echo "Build ${COUNT} ARM defconfigs in $MIN min, %SEC sec."

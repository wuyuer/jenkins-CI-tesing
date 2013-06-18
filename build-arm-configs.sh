#!/bin/bash

TOOLS=`dirname $0`

START_TIME=`date +%s`
COUNT=0

DEFCONFIGS=`(cd arch/arm/configs; echo *_defconfig)`
for defconfig in $DEFCONFIGS; do
  ${TOOLS}/build.sh --quiet arm ${defconfig}
  COUNT=$(( $COUNT + 1 ))
done

END_TIME=`date +%s`
BUILD_TIME=$(( $END_TIME - $START_TIME ))

echo "Build ${COUNT} ARM defconfigs in ${BUILD_TIME} seconds."

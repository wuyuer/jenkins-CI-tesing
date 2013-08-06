#!/bin/bash

TOOLS=`dirname $0`

START=`date +%s`
COUNT=0
PASS=0
FAIL=0

RESULTS_PASS=()
RESULTS_FAIL=()

DEFCONFIGS='allnoconfig '
DEFCONFIGS+=`(cd arch/arm/configs; echo *_defconfig)`

GIT_HASH=`git log -n1 --abbrev=8 --format=%h`
export OUTPUT_TOP="/run/shm/build-${GIT_HASH}"

echo -n "Build started: "
date
for defconfig in $DEFCONFIGS; do
  ${TOOLS}/build.sh --quiet arm ${defconfig}
  if [ $? = 0 ]; then
    PASS=$(( $PASS + 1 ))
    RESULTS_PASS+=(${defconfig})
  else
    FAIL=$(( $FAIL + 1 ))
    RESULTS_FAIL+=(${defconfig})
  fi
done

END=`date +%s`
BUILD_TIME=$(( $END - $START ))
MIN=$(( BUILD_TIME / 60 ))
SEC=$(( BUILD_TIME % 60 ))
COUNT=$(( $PASS + $FAIL ))

echo "Current commit: "
git log -n1 --oneline --abbrev=8 
echo -n "git desribe: "
git describe
echo

echo "Built ${COUNT} ARM defconfigs in $MIN min, $SEC sec. $PASS passed, $FAIL failed."

echo 
echo "--------------"
echo "Builds failed:"
echo "--------------"
for b in ${RESULTS_FAIL[@]}; do
  echo $b
done

echo 
echo "--------------"
echo "Builds passed:"
echo "--------------"
for b in ${RESULTS_PASS[@]}; do
  echo $b
done

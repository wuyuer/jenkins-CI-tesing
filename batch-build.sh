#!/bin/sh

TOOLS=~/work/kernel/tools/build-scripts

DIR=${1:-${HOME}/work/kernel/linux-2.6}
BRANCH=${2:-master}

if [ ! -e ${DIR} ]; then
  echo "ERROR: ${DIR} doesn't exist."
  exit 1
fi

cd ${DIR}

if [ -e .build-in-progress ]; then
  echo "ERROR: build in progress"
  exit 0
fi

git status
if [ $? != 0 ]; then
  echo "ERROR: something strange with git repo"
  exit 1
fi

git checkout master
git pull
git remote update
git checkout -f ${BRANCH}
BUILD=build-$(git describe)

echo ${DIR} ${BRANCH}

echo "Trying branch ${BRANCH}: ${BUILD}"
if [ -e ${BUILD} ]; then
   echo "${BUILD} already exists, not rebuilding."
   exit 0
fi

touch .build-in-progress
${TOOLS}/build-all-arm.sh
rm -f .build-in-progress

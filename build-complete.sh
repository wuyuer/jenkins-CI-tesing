#!/bin/bash

rm -rf *


#if [ $PUBLISH != true ]; then
#  echo "Skipping publish step.  PUBLISH != true."
#  exit 0
#fi

if [[ -z $TREE_NAME ]]; then
  echo "TREE_NAME not set.  Not publishing."
  exit 1
fi

if [[ -z $GIT_DESCRIBE ]]; then
  echo "GIT_DESCRIBE not set. Not publishing."
  exit 1
fi

if [[ -z $ARCH_LIST ]]; then
  echo "ARCH_LIST not set.  Not publishing."
  exit 1
fi

# Sanity prevails, do the copy
for arch in ${ARCH_LIST}; do
   sudo touch /var/www/images/kernel-ci/$TREE_NAME/$GIT_DESCRIBE/$arch.done
done

# Tell the dashboard to import the build.
echo "Build has now finished, reporting result to dashboard."
#curl -X POST -H "Authorization: d61fef42-ec72-4251-a10a-ae61da4a0745" -H "Content-Type: application/json" -d '{"job": "'$TREE_NAME'", "kernel": "'$GIT_DESCRIBE'", "git_branch": "'$BRANCH'", "git_commit": "'$COMMIT_ID'", "git_url": "'$TREE'"  }' http://192.168.1.108:8888/job
curl -X POST -H "Authorization: d61fef42-ec72-4251-a10a-ae61da4a0745" -H "Content-Type: application/json" -d '{"job": "'$TREE_NAME'", "kernel": "'$GIT_DESCRIBE'" }' http://192.168.1.108:8888/job

# Check if all builds for all architectures have finished. The magic number here is 3 (arm, arm64, x86)
# This magic number will need to be changed if new architectures are added.
export BUILDS_FINISHED=$(ls /var/www/images/kernel-ci/$TREE_NAME/$GIT_DESCRIBE/ | grep .done | wc -l)
if [[ BUILDS_FINISHED -eq 3 ]]; then
    echo "All builds have now finished, triggering testing..."
    if [ "$TREE_NAME" != "next" ] && [ "$TREE_NAME" != "arm-soc" ] && [ "$TREE_NAME" != "mainline" ] && [ "$TREE_NAME" != "stable" ] && [ "$TREE_NAME" != "rmk" ] && [ "$TREE_NAME" != "tegra" ]; then
        # Private Mailing List
        echo "Sending results to private mailing list"
        curl -X POST -H "Authorization: d61fef42-ec72-4251-a10a-ae61da4a0745" -H "Content-Type: application/json" -d '{"job": "'$TREE_NAME'", "kernel": "'$GIT_DESCRIBE'", "build_report": 1, "send_to": ["fellows@kernelci.org"], "format": ["txt", "html"], "delay": 10}' http://192.168.1.108:8888/send
        curl -X POST -H "Authorization: d61fef42-ec72-4251-a10a-ae61da4a0745" -H "Content-Type: application/json" -d '{"job": "'$TREE_NAME'", "kernel": "'$GIT_DESCRIBE'", "boot_report": 1, "send_to": ["fellows@kernelci.org"], "format": ["txt", "html"], "delay": 12600}' http://192.168.1.108:8888/send
    else
        # Public Mailing List
        echo "Sending results pubic mailing list"
        curl -X POST -H "Authorization: d61fef42-ec72-4251-a10a-ae61da4a0745" -H "Content-Type: application/json" -d '{"job": "'$TREE_NAME'", "kernel": "'$GIT_DESCRIBE'", "build_report": 1, "send_to": ["kernel-build-reports@lists.linaro.org"], "format": ["txt", "html"], "delay": 10}' http://192.168.1.108:8888/send
        curl -X POST -H "Authorization: d61fef42-ec72-4251-a10a-ae61da4a0745" -H "Content-Type: application/json" -d '{"job": "'$TREE_NAME'", "kernel": "'$GIT_DESCRIBE'", "boot_report": 1, "send_to": ["kernel-build-reports@lists.linaro.org"], "format": ["txt", "html"], "delay": 12600}' http://192.168.1.108:8888/send
    fi
fi

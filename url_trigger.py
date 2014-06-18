#!/usr/bin/env python
#
# Options:
#  -a build all defconfigs (otherwise just 'defconfig' is built)
#  -b branch name
#  -c commit ID
#  -d debug: just print URL, don't fetch it
#  -f defconfig list (space separated, in quotes)
#  -l architecture list (space separated, in quotes. otherwise just 'arm' is built)
#  -n tree name
#  -p publish
#  -t tree URL
#
import sys, os, urllib
import subprocess, getopt, random

#JENKINS_URL="https://ci.linaro.org/jenkins/view/people/job/khilman-kernel-build/"
JENKINS_URL="https://ci.linaro.org/jenkins/view/people/job/khilman-kbuilder/"

# Default URL parameters
params = {
    "token": "PleaseBeGentle",  # this is the "secret", please don't distribute
    "ARCH_LIST": "arm",
    "DEFCONFIG_LIST": "defconfig",
    "TREE": "git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux-2.6.git",
    "BRANCH": "master",
    "PUBLISH": False,
    "SUBMIT_TO_LAVA": False,
}

# Options
debug = False
commit_id = None

# Defaults
tree = None
tree_name = os.environ['USER'] + '-test'
this_tree = False  # set tree URL based on current git repo

try:
    opts, args = getopt.getopt(sys.argv[1:], "adb:c:f:l:n:pt:T:")
except getopt.GetoptError as err:
    print str(err) # will print something like "option -a not recognized"
    sys.exit(2)

all_defconfigs = False
for o, a in opts:
    if o == "-a":
        all_defconfigs = True
    if o == "-c":
        params['COMMIT_ID'] = a
    if o == "-b":
        params['BRANCH'] = a
    if o == "-d":
        debug = True
    if o == "-f":
        params['DEFCONFIG_LIST'] = a
    if o == "-l":
        params['ARCH_LIST'] = a
    if o == "-n":
        tree_name = a
    if o == "-p":
        params['PUBLISH'] = True
    if o == "-t":
        tree = a
    if o == "-T":
        this_tree = a

if this_tree and os.path.exists(".git"):
    cmd = "git config --get remote.%s.url" %this_tree
    tree = subprocess.check_output(cmd, shell=True)

params['TREE_NAME'] = tree_name
if tree:
    params['TREE'] = tree

# Add all available defconfigs to DEFCONFIG_LIST
if all_defconfigs:
    if os.path.exists('arch/arm/configs'):
        defconfigs = subprocess.check_output('(cd arch/arm/configs; echo *_defconfig)', shell=True)
        params['DEFCONFIG_LIST'] += ' ' + defconfigs

url = "%sbuildWithParameters?%s" %(JENKINS_URL, urllib.urlencode(params))
if debug:
    print url

# This will trigger the build
if not debug:
    f = urllib.urlopen(url)
    result = f.read()

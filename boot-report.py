#!/usr/bin/env python

import os, sys, subprocess, glob
import tempfile, getopt
import util
import json

maillog = None
mail_to = None
url_base = "http://storage.armcloud.us/kernel-ci"
boot_url_base = "http://status.armcloud.us/boot/all/job"
build_url_base = "http://status.armcloud.us/build"

def usage():
    print "Usage: %s [-m <email address>] <base>" %(sys.argv[0])

try:
    opts, args = getopt.getopt(sys.argv[1:], "m:l:")
except getopt.GetoptError as err:
    print str(err)
    usage()
    sys.exit(1)

for o, a in opts:
    if o == '-l':
        maillog = a
    if o == '-m':
        mail_to = a

dir = args[0]
base = os.path.dirname(dir)

if base == '.' or base == '':
    base = os.getcwd()

if not os.path.exists(dir):
    print "ERROR: %s does not exist" %dir

builds = {}
total_fail_count = 0
total_pass_count = 0
total_offline_count = 0
total_board_count = 0
for build in os.listdir(dir):
    boards = {}
    build_fail_count = 0
    build_pass_count = 0
    build_offline_count = 0
    path = os.path.join(dir, build)
    for jsonfile in glob.glob('%s/boot-*.json' %path):
        (prefix, suffix) = os.path.splitext(jsonfile) 
        board = os.path.basename(prefix)[5:] # drop 'boot-'

        fp = open(jsonfile)
        boot_meta = json.load(fp)
        fp.close()
        result = boot_meta.get("boot_result", "UNKNOWN")

        total_board_count += 1
        if result == 'PASS':
            build_pass_count += 1
            total_pass_count += 1
        elif result == 'OFFLINE':
            build_offline_count += 1
            total_offline_count += 1
        else:
            build_fail_count += 1
            total_fail_count += 1

        warnings = boot_meta.get("boot_warnings", 0)
        time = boot_meta.get("boot_time", 0)
        result_desc = boot_meta.get("boot_result_description", None)
        boards[board] = (result, time, warnings, result_desc)

    if len(boards) > 0:
        builds[build] = (boards, build_fail_count, build_pass_count, build_offline_count)

# Don't send mail if there were no builds
if len(builds) == 0:
    print "WARNING: No boot logs found, Giving up."
    sys.exit(1)

# Extract tree/branch from report header
(tree_branch, describe, commit) = util.get_header_info(base)

tree = os.path.basename(base)
url_base = url_base + "/%s/%s" %(tree, dir)
boot_url = boot_url_base + "/%s/kernel/%s/" %(tree, dir)
build_url = build_url_base + "/%s/kernel/%s/" %(tree, dir)

offline_summary = ""
if total_offline_count:
    offline_summary = ", %d offline" %total_offline_count

# Unbuffer stdout so 'print' and subprocess output intermingle correctly
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

#
#  Log to a file as well as stdout (for sending with msmtp)
#
tmplog = tempfile.mktemp(suffix='.log', prefix='boot-report')
#if not maillog:
#    maillog = tempfile.mktemp(suffix='.log', prefix='boot-report-mail')

#if maillog:
if tmplog:
    stdout_save = sys.stdout
    tee = subprocess.Popen(["tee", "%s" %tmplog], stdin=subprocess.PIPE)
    os.dup2(tee.stdin.fileno(), sys.stdout.fileno())
    os.dup2(tee.stdin.fileno(), sys.stderr.fileno())

print "Full Build report:", build_url
print "Full Boot report: ", boot_url
print
if tree_branch:
    print 'Tree/Branch:', tree_branch
if describe:
    print 'Git describe:', describe
if commit:
    print 'Commit:', commit
print

# Failure summary
if total_fail_count:
    msg =  "Failed boot tests"
    print msg
    print '=' * len(msg)
    for build in builds:
        boards = builds[build][0]
        fail_count = builds[build][1]
        if not fail_count:
            continue
        for board in boards:
            report = boards[board]
            result = report[0]
            result_desc = report[3]
            if result == 'FAIL':
                print '%28s: %8s:    %s' %(board, result, build)
                if result_desc:
                    print ' ' * 33, result_desc
                if result_desc and result_desc.startswith("Kernel build failed"):
                    print ' ' * 27, "      %s/%s/build.log" %(url_base, build)
                else:
                    print ' ' * 27, "      %s/%s/boot-%s.html" %(url_base, build, board)
                
    print

# Offline summary
if total_offline_count:
    msg =  "Offline boards (unable to connect to serial console)"
    print msg
    print '=' * len(msg)
    for build in builds:
        boards = builds[build][0]
        offline_count = builds[build][3]
        if not offline_count:
            continue
        for board in boards:
            report = boards[board]
            result = report[0]
            if result == 'OFFLINE':
                print '%28s: %8s:    %s' %(board, result, build)
    print

# Passing Summary
if total_pass_count:
    msg = "Full Report"
    print msg
    print '=' * len(msg)
    for build in builds:
        boards = builds[build][0]
        print
        print build
        print '-' * len(build)
        for board in boards:
            report = boards[board]
            result = report[0]
            time = report[1]
            warnings = report[2]
            result_desc = report[3]
            print "%28s     %d min %4.1f sec: %8s" \
                %(board, time / 60, time % 60, result, ),
            if warnings:
                print " (Warnings: %d)" %warnings
            elif result_desc:
                print " -", result_desc
            else:
                print

sys.stdout.flush()
sys.stdout = stdout_save

# if no passing tests, only send mail to me
if total_pass_count == 0 and mail_to:
    mail_to = "khilman@linaro.org"

mail_headers = """From: Kevin's boot bot <khilman@kernel.org>
To: %s
Subject: %s boot: %d boots: %d pass, %d fail%s (%s)

""" %(mail_to, tree_branch, total_board_count, total_pass_count, total_fail_count, offline_summary, describe)

# Create the final report with mail headers
if maillog:
    # Write headers
    fp = open(maillog, "w")
    fp.write(mail_headers)
    fp.close()

    subprocess.call("cat %s >> %s" %(tmplog, maillog), shell=True)
    mail_cmd = 'cat %s | msmtp --read-envelope-from -t --' %(maillog)
    if mail_to:
        subprocess.check_output(mail_cmd, shell=True)

if tmplog and os.path.exists(tmplog):
    os.remove(tmplog)
if maillog:
    if os.path.exists(maillog):
        if maillog.startswith('/tmp'):
            os.remove(maillog)
    else:
        print "WARNING: mail log %s doesn't exist!" %maillog

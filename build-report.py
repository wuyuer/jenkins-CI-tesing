#!/usr/bin/env python
#
# Usage: build-report <base>
# 
#   Where <base> is the root directory containing all the build output
#
import os, sys, subprocess
import tempfile, getopt
import util
import json

log = 'build.log'
sep = '-' * 79

mail_to = None

def usage():
    print "Usage: %s [-m <email address>] <base>" %(sys.argv[0])

try:
    opts, args = getopt.getopt(sys.argv[1:], "m:")
except getopt.GetoptError as err:
    print str(err)
    usage()
    sys.exit(1)

for o, a in opts:
    if o == '-m':
        mail_to = a

if len(args) < 1:
    usage()
    sys.exit(1)

dir = os.path.abspath(args[0])
base = os.path.abspath(os.path.dirname(dir))

if not os.path.exists(dir):
    print "ERROR: %s does not exist" %dir

# format: (result, error list, warning list, mismatch list)
report = {}
report_good = {}

pass_count = 0
fail_count = 0
total_count = 0
warnings_all = {}
mismatch_all = {}
errors_all = {}

def uniqify(d):
    l = zip(d.values(), d.keys())
    l.sort()
    l.reverse()
    return l

def remove_prefix(arr, base):
    """Remove string <base> from beginning of each array element"""
    for i in range(len(arr)):
        if arr[i].find(base, 0) == 0:
            arr[i] = arr[i][len(base) + 1:]

# Parse the logs
for build in os.listdir(dir):

    buildlog = os.path.join(dir, build, log)
    # Ignore build dirs with no build log
    if not os.path.exists(buildlog):
        continue

    total_count += 1

    pass_fail = 'UNKNOWN'
    build_json = os.path.join(dir, build, 'build.json')
    if os.path.exists(build_json):
        f = open(build_json, 'r')
        build_meta = json.load(f, encoding="utf-8")
        f.close()

        pass_fail = build_meta["build_result"]
        if pass_fail == 'PASS':
            pass_count += 1
        else:
            fail_count += 1
    else:
        print build_json, "doesn't exist."

    # Error messages, strip of the path prefix
    err_cmd = 'grep [Ee]rror: %s | cat' %buildlog
    errors = subprocess.check_output(err_cmd, shell=True).splitlines()
    # Look for linker errors too
    err_cmd = 'fgrep "undefined reference to" %s | cat' %buildlog
    errors += subprocess.check_output(err_cmd, shell=True).splitlines()
    remove_prefix(errors, base)

    # Some errors start with ERROR:
    # DTB compiler gives 'ERROR' (without trailing :)
    err_cmd = 'grep ^ERROR %s | cat' %buildlog
    errors2 = subprocess.check_output(err_cmd, shell=True).splitlines()
    for e in errors2:
        errors.append(e)

    for e in errors:
        errors_all[e] = errors_all.setdefault(e, 0) + 1

    warn_cmd = 'fgrep warning: %s | ' \
        'fgrep -v "TODO: return_address should use unwind tables" | ' \
        'fgrep -v "NPTL on non MMU needs fixing" | ' \
        'fgrep -v "Sparse checking disabled for this file" | cat' %buildlog
    warnings = subprocess.check_output(warn_cmd, shell=True).splitlines()
    remove_prefix(warnings, base)
    for w in warnings:  
        warnings_all[w] = warnings_all.setdefault(w, 0)  + 1

    mismatch_cmd = 'fgrep "Section mismatch" %s | cat' %(buildlog)
    mismatches = subprocess.check_output(mismatch_cmd, shell=True).splitlines()
    for m in mismatches:
        mismatch_all[m] = mismatch_all.setdefault(m, 0) + 1

    if len(errors) or len(warnings) or len(mismatches):
        report[build] = (pass_fail, errors, warnings, mismatches)
    else:
        report_good[build] = (pass_fail, errors, warnings, mismatches)
        

if total_count == 0:
    print "No builds found."
    sys.exit(0)

# Calculate Summaries
errors = uniqify(errors_all)
error_count = len(errors)
warns = uniqify(warnings_all)
warning_count = len(warns)
mismatches = uniqify(mismatch_all)
mismatch_count = len(mismatches)

build_time = 0
if os.path.exists('timestamp.start') and os.path.exists('timestamp.end'):
    try:
        t_start = int(open('timestamp.start').readline().rstrip())
        t_end = int(open('timestamp.end').readline().rstrip())
        build_time = t_end - t_start
    except IOError:
        pass

(tree_branch, describe, commit) = util.get_header_info(base)

#
#  Log to a file as well as stdout (for sending with msmtp)
#
maillog = tempfile.mktemp(suffix='.log', prefix='build-report')
mail_headers = """From: Kevin Hilman build bot <khilman+build@linaro.org>
To: %s
Subject: %s build: %d failures %d warnings (%s)
""" %(mail_to, tree_branch, fail_count, warning_count, describe)

if maillog:
    stdout_save = sys.stdout
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Unbuffer output
    tee = subprocess.Popen(["tee", "%s" %maillog], stdin=subprocess.PIPE)
    os.dup2(tee.stdin.fileno(), sys.stdout.fileno())
    os.dup2(tee.stdin.fileno(), sys.stderr.fileno())
    print mail_headers

# Print report
if os.path.exists('.git'):
    print 'Tree/Branch:', tree_branch
    print 'Git describe:', describe
    print 'Commit:', commit
if build_time:
    print 'Build Time: %d min %d sec' %(build_time/60, build_time%60)

formatter = "{:6.2f}"
print
print "Passed: %4d / %d   (%6.2f %%)" \
    %(pass_count, total_count, float(pass_count) / total_count * 100)
print "Failed: %4d / %d   (%6.2f %%)" \
    %(fail_count, total_count, float(fail_count) / total_count * 100)
unknown_count = total_count - (pass_count + fail_count)
if unknown_count:
    print "Unknown: %3d / %d   (%6.2f %%)" \
        %(unknown_count, total_count, float(unknown_count) / total_count * 100)


print
print "Errors:", error_count
print "Warnings:", warning_count
print "Section Mismatches:", mismatch_count

# Build failure summary:
if fail_count:
    print
    print "Failed defconfigs:"
    for build in report:
        pass_fail = report[build][0]
        if pass_fail == 'FAIL':
            print "\t%s" %build
        
    print
    print "Errors:"
    for build in report:
        pass_fail = report[build][0]
        if pass_fail == 'PASS':
            continue

        err = report[build][1]
        if not len(err):
            continue

        print
        print "\t%s" %build
        for e in err:
            print e
    
print
print sep

# Issues summary
print "defconfigs with issues (other than build errors):"
for build in report:
    w = report[build][2]
    m = report[build][3]
    if not (len(w) or len(m)):
        continue

    print "   ",
    print "%3d warnings " %len(w),
    print "%3d mismatches " %len(m),
    print ": %s" %build

print
print sep

# Errors Summary
if error_count:
    print
    print "Errors summary:", error_count
    for e in errors:
        print "\t%3d %s" %(e[0], e[1])

# Warnings Summary (for all builds)
if warning_count:
    print
    print "Warnings Summary:", warning_count
    for w in warns:
        print "\t%3d %s" %(w[0], w[1])

# Mismatch Summary (for all builds)
if mismatch_count:
    print
    print "Section Mismatch Summary:", mismatch_count
    for m in mismatches:
        print "\t%3d %s" %(m[0], m[1])

print "\n" * 2
print "=" * 79
print "Detailed per-defconfig build reports below:"
print

# per-build report
for build in report:
    pass_fail = report[build][0]
    errors = report[build][1]
    warnings = report[build][2]
    mismatches = report[build][3]

    print
    print sep
    print build, \
        ": %s, %d errors, %d warnings, %d section mismatches" \
        %(pass_fail, len(errors), len(warnings), len(mismatches))

    if len(warnings) or len(errors) or len(mismatches):
        if len(errors):
            print
            print "Errors:"
            for err in errors:
                print '\t', err

        if len(warnings):
            print
            print "Warnings:"
            for warn in warnings:
                print '\t', warn

        if len(mismatches):
            print
            print "Section Mismatches:"
            for m in mismatches:
                print '\t', m

print sep
print
print "Passed with no errors, warnings or mismatches:"
print
for build in report_good:
    print build

# Mail the final report
if maillog:
    sys.stdout.flush()
    sys.stdout = stdout_save
    if mail_to:
        subprocess.check_output('cat %s | msmtp --read-envelope-from -t --' %maillog, shell=True)
    if os.path.exists(maillog):
        os.remove(maillog)
    else:
        print "WARNING: mail log %s doesn't exist!" %maillog

retval = 0
if fail_count:
    retval = 1

sys.exit(retval)

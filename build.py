#!/usr/bin/env python
#
# NOTES:
# - override ARCH and CROSS_COMPILE using environment varialbes
#
# TODO
#
import os
import sys
import subprocess
import getopt
import tempfile
import glob
import shutil
import re

cross_compilers = {
    "arm": "arm-linux-gnueabi-",
    "arm64": "aarch64-linux-gnu-",
    "i386": None,
    "x86_64": None,
}

# Defaults
arch = "arm"
cross_compile = cross_compilers[arch]
git_describe = None
git_commit = None
ccache = None
make_threads = 2
kbuild_output_prefix = 'build'
silent = True
build_target = None
build_log = None
build_log_f = None

def usage():
    print "Usage:", sys.argv[0], "[options] [make target]"
    
def do_make(target=None, log=False):
    make_args = ''
    make_args += "-j%d -k " %make_threads
    if silent:
        make_args += "-s "
    make_args += "ARCH=%s " %arch
    if cross_compile:
        make_args += "CROSS_COMPILE=%s " %cross_compile
    if ccache:
        prefix = ''
        if cross_compile:
            prefix = cross_compile
        make_args += 'CC="ccache %sgcc" ' %prefix
    if kbuild_output:
        make_args += "O=%s " %kbuild_output
    if target:
        make_args += target
    make_cmd = 'make %s' %make_args
    print make_cmd

    make_stdout = None
    if log:
        build_log_f.write("#\n# " + make_cmd + "\n#\n")
        make_stdout = build_log_f
    p1 = subprocess.Popen(make_cmd , shell=True,
                          stdout=make_stdout,
                          stderr=subprocess.STDOUT,
    )
#    p2 = subprocess.Popen("tee --append %s" %os.path.join(kbuild_output, "build.log"),
#                          shell=True,
#                          stdin=p1.stdout)
#    p2.communicate()
    p1.communicate()
    return p1.wait()

#
# cmdline args
#
defconfig = None
kconfig_tmpfile = None
kconfig_tmpfile_fd = None
kconfig_frag = None
frag_names = []
install = False

# temp frag file: used to collect all kconfig fragments
kconfig_tmpfile_fd, kconfig_tmpfile = tempfile.mkstemp(prefix='kconfig-')

try:
    opts, args = getopt.getopt(sys.argv[1:], "c:si")

except getopt.GetoptError as err:
    print str(err) # will print something like "option -a not recognized"
    sys.exit(2)
for o, a in opts:
    if o == '-c':
        defs = a.split('+')
        for a in defs:
            if os.path.exists("arch/%s/configs/%s" %(arch, a)):
                defconfig = a
            elif a == "defconfig" or re.match("all(\w*)config", a):
                defconfig = a
            elif os.path.exists(a):
                # Append fragment contents to temp frag file
                frag = open(a)
                os.write(kconfig_tmpfile_fd, "\n# fragment from: %s\n" %a)
                for line in frag:
                    os.write(kconfig_tmpfile_fd, line)
                frag.close()
                frag_names.append(os.path.basename(os.path.splitext(a)[0]))
            elif a.startswith("CONFIG_"):
                # add to temp frag file
                os.write(kconfig_tmpfile_fd, a + "\n")
                os.fsync(kconfig_tmpfile_fd)
                frag_names.append(a)
            else:
                print "ERROR: kconfig file/fragment (%s) doesn't exist" %a
                sys.exit(1)

    if o == '-i':
        install = True
    if o == '-s':
        silent = not silent

# Set number of make threads to number of local processors + 2
if os.path.exists('/proc/cpuinfo'):
    output = subprocess.check_output('grep -c processor /proc/cpuinfo',
                                     shell=True)
    make_threads = int(output) + 2

# ARCH
if os.environ.has_key('ARCH'):
    arch = os.environ['ARCH']
else:
    os.environ['ARCH'] = arch

# CROSS_COMPILE
if cross_compilers.has_key(arch):
    cross_compile = cross_compilers[arch]
if os.environ.has_key('CROSS_COMPILE'):
    cross_compile = os.environ['CROSS_COMPILE']
else:
    if cross_compile:
        os.environ['CROSS_COMPILE'] = cross_compile

# KBUILD_OUTPUT
kbuild_output = kbuild_output_prefix
if os.environ.has_key('KBUILD_OUTPUT'):
    kbuild_output = os.environ['KBUILD_OUTPUT']
else:
    os.environ['KBUILD_OUTPUT'] = kbuild_output
if not os.path.exists(kbuild_output):
    os.makedirs(kbuild_output)
build_log = os.path.join(kbuild_output, "build.log")
build_log_f = open(build_log, 'w', 0)

# ccache
ccache = None
ccache_dir = None
if not os.environ.has_key('CCACHE_DISABLE'):
    ccache = subprocess.check_output('which ccache | cat', shell=True).strip()
if ccache and len(ccache):
    if os.environ.has_key('CCACHE_DIR'):
        ccache_dir = os.environ['CCACHE_DIR']
    else:
        #ccache_dir = os.path.join(os.getcwd(), '.ccache' + '-' + arch)
        ccache_dir = os.path.join(os.getcwd(), '.ccache')
        os.environ['CCACHE_DIR'] = ccache_dir
else:
    ccache_dir = None

# Misc. env overrides
if os.environ.has_key('GIT_DESCRIBE'):
    git_describe = os.environ['GIT_DESCRIBE']

# Gather env/info
if os.path.exists('.git'):
    git_commit = subprocess.check_output('git log -n1 --format=%H', shell=True).strip()
    git_url = subprocess.check_output('git config --get remote.origin.url', shell=True).strip()
    git_branch = subprocess.check_output('git rev-parse --abbrev-ref HEAD', shell=True).strip()
    if not git_describe:
        git_describe = subprocess.check_output('git describe', shell=True).strip()

cc_cmd = "gcc -v 2>&1"
if cross_compile:
    cc_cmd = "%sgcc -v 2>&1" %cross_compile
gcc_version = subprocess.check_output(cc_cmd, shell=True).splitlines()[-1]

# for var in ['ARCH', 'CROSS_COMPILE', 'CCACHE_DIR', 'KBUILD_OUTPUT']:
#     if os.environ.has_key(var):
#         val = os.environ[var]
#     else:
#         val = ""
#     print "#", var, "=", val

#
# Config
#
dot_config = os.path.join(kbuild_output, '.config')

if defconfig:
    if len(frag_names):
        kconfig_frag = os.path.join(kbuild_output, 'frag-' + '+'.join(frag_names) + '.config')
        shutil.copy(kconfig_tmpfile, kconfig_frag)
        cmd = "scripts/kconfig/merge_config.sh -O %s arch/%s/configs/%s %s > /dev/null 2>&1" %(kbuild_output, arch, defconfig, kconfig_frag)
        print cmd
        subprocess.call(cmd, shell = True)
    else:
        do_make(defconfig)
elif os.path.exists(dot_config):
    print "Re-using .config:", dot_config
    defconfig = "existing"
else:
    print "ERROR: Missing kernel config"
    sys.exit(0)

# 
# Build kernel
#
if len(args) >= 1:
    build_target = args[0]
result = do_make(build_target, log=True)

# Build modules
modules = None
if result == 0:
    modules = not subprocess.call('grep -cq CONFIG_MODULES=y %s' %dot_config, shell=True) 
    if modules:
        result |= do_make('modules', log=True)

# Check errors/warnings
warn_cmd = 'grep -v ^# %s | fgrep warning: | ' \
           'fgrep -v "TODO: return_address should use unwind tables" | ' \
           'fgrep -v "NPTL on non MMU needs fixing" | ' \
           'fgrep -v "Sparse checking disabled for this file" | cat' %build_log
warnings = subprocess.check_output(warn_cmd, shell=True).splitlines()
num_warnings = len(warnings)
if num_warnings:
    print "\nBuild Warnings:", num_warnings
    for warn in warnings:
        print "   ", warn

err_cmd = 'grep -v ^# %s | fgrep -i error: | cat' %build_log
errors = subprocess.check_output(err_cmd, shell=True).splitlines()
num_errors = len(errors)
if num_errors:
    print "\nBuild Errors:", num_errors
    for err in errors:
        print "   ", err

# Install
if install:
    install_path = os.path.join(os.getcwd(), '_install_', git_describe)
    install_path = os.path.join(install_path, '-'.join([arch, defconfig]))
    if len(frag_names):
        install_path += '+' + '+'.join(frag_names)

    os.environ['INSTALL_PATH'] = install_path
    if not os.path.exists(install_path):
        os.makedirs(install_path)
    
    boot_dir = "%s/arch/%s/boot" %(kbuild_output, arch)

    text_offset = -1
    system_map = os.path.join(kbuild_output, "System.map")
    if os.path.exists(system_map):
        virt_text = subprocess.check_output('grep " _text" %s' %system_map, shell=True).split()[0]
        text_offset = int(virt_text, 16) & (1 << 30)-1  # phys: cap at 1G
        shutil.copy(system_map, install_path)
    else:
        system_map = None
        text_offset = None

    dot_config_installed = os.path.join(install_path, "kernel.config")
    shutil.copy(dot_config, dot_config_installed)

    shutil.copy(build_log, install_path)
    if kconfig_frag:
        shutil.copy(kconfig_frag, install_path)

    kimage_file = None
    kimages = glob.glob("%s/*Image" %boot_dir)
    if len(kimages) == 1:
        kimage_file = kimages[0]
    elif len(kimages) > 1:
        kimage_file = kimages[-1]
        for kimage in kimages:
            if os.path.basename(kimage).startswith('z'):
                kimage_file = kimage
        print "FIXME: need deal with multiple kernel images.  Picking %s from %s" \
            %(kimage_file, kimages)

    if kimage_file:
        shutil.copy(kimage_file, install_path)

    dtbs = glob.glob("%s/dts/*.dtb" %boot_dir)
    if len(dtbs):
        dtb_dest = os.path.join(install_path, 'dtbs')
        if not os.path.exists(dtb_dest):
            os.makedirs(dtb_dest)
        for dtb in dtbs:
            shutil.copy(dtb, dtb_dest)
    else:
        dtb_dest = None

    #do_make('install')
    if modules:
        tmp_mod_dir = tempfile.mkdtemp()
        os.environ['INSTALL_MOD_PATH'] = tmp_mod_dir
        do_make('modules_install')
        modules_tarball = "modules.tar.xz"
        cmd = "(cd %s; tar -Jcf %s lib/modules)" %(tmp_mod_dir, modules_tarball)
        subprocess.call(cmd, shell=True)
        shutil.copy(os.path.join(tmp_mod_dir, modules_tarball), install_path)
        shutil.rmtree(tmp_mod_dir)

    # Generate meta data
    build_meta = os.path.join(install_path, 'build.meta')
    f = open(build_meta, 'w')
    f.write("[DEFAULT]\n") # make it easy for python ConfigParser
    f.write("build_result: ")
    if result == 0:
        f.write("PASS\n")
    else:
        f.write("FAIL\n")
    f.write("\n")

    f.write("arch: %s\n" %arch)
    f.write("cross_compile: %s\n" %cross_compile)
    f.write("compiler_version: %s\n" %gcc_version)
    f.write("git_url: %s\n" %git_url)
    f.write("git_branch: %s\n" %git_branch)
    f.write("git_describe: %s\n" %git_describe)
    f.write("git_commit: %s\n" %git_commit)
    f.write("defconfig: %s\n" %defconfig)
    if kconfig_frag:
        f.write("kconfig_fragments: %s\n" %os.path.basename(kconfig_frag))
    else:
        f.write("kconfig_fragments:\n")
    f.write("\n")

    f.write("kernel_image: ")
    if kimage_file:
        f.write("%s\n" %os.path.basename(kimage_file))
    else:
        f.write("\n")
    
    f.write("kernel_config: %s\n" %os.path.basename(dot_config_installed))
    f.write("system_map: ")
    if system_map:
        f.write("%s\n" %os.path.basename(system_map))
    else:
        f.write("\n")

    f.write("text_offset: ")
    if text_offset:
        f.write("0x%08x\n" %text_offset)
    else:
        f.write("\n")

    f.write("dtb_dir: ")
    if dtb_dest:
        f.write("%s\n" %os.path.basename(dtb_dest))
    else:
        f.write("\n")

    f.write("modules: ")
    if modules and modules_tarball:
        f.write("%s\n" %modules_tarball)
    else:
        f.write("\n")

    f.write("\n")
    f.write("build_log: %s\n" %os.path.basename(build_log))
    f.write("build_errors: %d\n" %num_errors);
    f.write("build_warnings: %d\n" %num_warnings);
    f.close()

#
# Cleanup
#
if kconfig_tmpfile:
    os.unlink(kconfig_tmpfile)

sys.exit(result)

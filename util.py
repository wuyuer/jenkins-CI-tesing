import os, sys, subprocess

def get_header_info(base=''):
    tree_branch = None
    describe = None
    commit = None

    if os.environ.has_key('GIT_BRANCH'):
        tree_branch = os.environ['GIT_BRANCH']

    if os.environ.has_key('GIT_DESCRIBE'):
        describe = os.environ['GIT_DESCRIBE']

    if os.path.exists('.git'):
        describe = subprocess.check_output('git describe', shell=True).rstrip()
        commit = subprocess.check_output('git log -n1 --oneline --abbrev=10',
                                         shell=True)
        if not tree_branch:
            tree_branch = subprocess.check_output('git describe --all',
                                                  shell=True).rstrip()
            i = tree_branch.find('/')
            if i > 0:
                tree_branch = tree_branch[i+1:]

    return (tree_branch, describe, commit)

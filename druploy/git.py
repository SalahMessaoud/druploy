from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import *


class GitRepository(object):
    def __init__(self, url=None):
        self.url = url

    def clone(self, checkout_dir=None):
        with cd(checkout_dir):
            return run("git clone {0} .".format(self.url))


class GitWorkingCopy(object):
    def __init__(self, path=None):
        self.path = path

    def cloned(self):
        with cd(self.path):
            return exists('.git')

    def checkout(self, revision_or_branch):
        with cd(self.path):
            return run("git checkout {0}".format(revision_or_branch))

    def prune(self):
        with cd(self.path):
            return run("git remote prune origin")

    def pull(self):
        with cd(self.path):
            return run("git pull")

    def branch(self):
        with cd(self.path):
            return run("git branch 2>/dev/null| sed -n '/^\*/s/^\* //p'")

    def revision(self):
        with cd(self.path):
            return run("git rev-parse --short HEAD")




import os
from os.path import join
from fabric.api import *
from fabric.utils import *
from fabric.context_managers import *
from fabric.contrib.files import exists
from druploy.deployment import *
from druploy.git import *

class CodeDeploymentSource(GitRepository, DeploymentSource):
    def __init__(self, deployment=None, url=None, branch=None, revision=None):
        GitRepository.__init__(self, url)
        DeploymentSource.__init__(self, "code")

        self.deployment = deployment

        if (branch is None and revision is None) or (branch is not None and revision is not None):
            raise ValueError("You must specify either a branch OR a revision")
        self.branch = branch
        self.revision = revision
        self.revision_or_branch = branch if branch is not None else revision


class CodeDeploymentDestination(GitWorkingCopy, DeploymentDestination):
    def __init__(self, deployment):
        DeploymentDestination.__init__(self, "code")
        self.deployment = deployment
        GitWorkingCopy.__init__(self, Path(self.deployment.server, self.deployment.path.__str__(), "code", "destination", "data"))

        self.drupal_site = DrupalSite(self.deployment.server, str(self.path))

    def collect(self, source=None):
        if not self.cloned():
            source.clone(self.path)
            
        self.checkout(source.revision_or_branch)
        # TODO: Do not prune when we copy this to working copy functionality
        self.prune()   
        self.pull()

    def prepare(self, source=None):
        self.checkout(source.revision_or_branch)
        self.deployment.server.chown(self.drupal_site.path, 'admin', 'www-data', True, True)

    def deploy(self, source=None):
        Utils.notice("Deploying code")
        #env.server.symlink(self.full_path, "code")



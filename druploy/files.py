import os
from datetime import datetime
from fabric.api import *
from fabric.utils import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.files import exists
from druploy.utils import *
from druploy.deployment import *

class Files(object):
    def __init__(self, deployment):
        self.deployment = deployment
        self.server = self.deployment.server

    def generate_parameters(self, tag):
        parameters = {
            "host": self.server.hostname(),
            "branch": self.deployment.drupal_site.branch(),
            "revision": self.deployment.drupal_site.revision(),
            "timestamp": Asset.timestamp(),
            "deployment_type": self.deployment.deployment_type,
            "project": self.deployment.project.name,
            "deployment": self.deployment.name,
            "tag": tag,
        }
        parameters["asset_type"] = "files"
        return parameters

    def setup(self):
        self.server.chmod(self.deployment.drupal_site.path.sites.default.files, 0777, recursive=True)

    def export(self, tag, path):
        filename = Asset.parse_uid(self.generate_parameters(tag))
        filepath = join(path, filename)

        with settings(**self.server.settings()):
            run("cp -rp {0} {1}".format(self.deployment.drupal_site.path.files, filepath))
        return filepath


class FilesSource(Files, DeploymentSource):
    def __init__(self, deployment):
        Files.__init__(self, deployment)
        DeploymentSource.__init__(self, 'files')
        self.path = Path(self.server, str(self.deployment.path), 'files')
        self.assets = AssetStore(self.server, str(self.path.source), ['files'])

    def snapshot(self):
        filepath = self.export('source', self.path.source)
        return Asset(self.server, filepath)


class UpdateFromServerFilesSource(FilesSource):
    def __str__(self):
        return "Update files from server"

    def __init__(self, deployment):
        FilesSource.__init__(self, deployment)

    def collect(self, destination):
        self.asset = self.snapshot()

    def send(self, destination):
        self.server.transfer(self.asset.path, destination.server, destination.path.source)


class ResetToSnapshotFilesSource(FilesSource):
    def __str__(self):
        return "Reset files to a snapshot"

    def __init__(self, deployment):
        FilesSource.__init__(deployment)

    def collect(self, destination):
        try:
            self.asset = self.assets.match(self.parameters('source'), ignore=['timestamp', 'revision']).list()[0]
        except IndexError, e:
            self.asset = self.snapshot()

    def send(self, destination):
        try:
            destination.assets.match(self.asset.parameters(), ignore=['timestamp', 'revision']).list()[0]
        except IndexError, e:
            self.server.transfer(self.asset.path, destination.server, destination.path.source)


class FilesDestination(Files, DeploymentDestination):
    def __str__(self):
        return 'Copy to files destination'

    def __init__(self, deployment):
        Files.__init__(self, deployment)
        DeploymentDestination.__init__(self, 'files')
        self.path = Path(self.server, str(self.deployment.path), 'files')
        self.assets = AssetStore(self.server, str(self.path), ['files'])

    def pre_deploy(self, source):
        return
        if not self.exists():
            self.create()
        self.snapshot("pre-deploy")

    def deploy(self, source):
        source_directory = join(self.path.source, source.asset.uid)
        destination_directory = join(self.path.destination.data, source.asset.uid)
        run("cp -rp {0} {1}".format(source_directory, destination_directory))

        files_directory_path = join(self.deployment.drupal_site.path.sites.default, 'files')
        self.server.rmfile(files_directory_path)
        self.server.symlink(destination_directory, files_directory_path)

    def post_deploy(self, source):
        return
        self.snapshot("post-deploy")


import os
from os.path import join
import re
from fabric.context_managers import *
from druploy.exceptions import *
from druploy.utils import *
from druploy.project import *
from druploy.drupal import *

class Deployment(object):
#    steps = ["collect", "send", "prepare", "pre_deploy", "deploy", "post_deploy", "activate"]
    steps = ["collect", "send", "prepare", "deploy"]
    folders = ["code", "database", "files"]

    def __str__(self):
        return "{0} deployment {1} at {2}".format(self.deployment_type, self.name, self.path)

    def __init__(self, project=None, deployment_type=None, name=None):
        if project is None:
            raise ValueError("You must specify a project")
        self.project = project

        if name is None:
            raise ValueError("You must specify a deployment name")
        self.name = name

        self.server = project.server
        self.deployment_type = deployment_type

        # Default empty deployment maps
        self.code = DeploymentMap(DeploymentSource("code"), DeploymentDestination("code"))
        self.files = DeploymentMap(DeploymentSource("files"), DeploymentDestination("files"))
        self.database = DeploymentMap(DeploymentSource("database"), DeploymentDestination("database"))

        self.path = Path(self.server, str(self.project.path), "deployments", self.name)
        self._drupal_site = None
        self.assets = AssetStore(self.server, str(self.path), max_depth=6)

    def run(self):
        for asset in [self.code, self.database, self.files]:
            for step in Deployment.steps:
                if hasattr(asset.source, 'deployment'):
                    with settings(**asset.source.deployment.server.settings()):
                        getattr(asset.source, step)(asset.destination)
                    with settings(**asset.destination.deployment.server.settings()):
                        getattr(asset.destination, step)(asset.source)
                else:
                    Utils.notice("Nothing to do on a placeholder asset, skipping")

    @property
    def drupal_site(self):
        if self._drupal_site is None:
            try:
                self._drupal_site = DrupalSite.find(self.server, str(self.path))[0]
            except IndexError:
                self._drupal_site = DrupalSite(self.server, None)
        return self._drupal_site

    @drupal_site.setter
    def drupal_site(self, value):
        self._drupal_site = value

    def validate(self):
        return True


class DeploymentAsset(object):
    def __init__(self, asset_type=None):
        self.asset_type = asset_type

    def __getattr__(self, name):
        if name in Deployment.steps:
            def nostep(self):
                Utils.notice("{0} not implemented in {1} asset of type '{2}', passing".format(name, self.asset_type, self.__class__.__name__))
            return nostep
        else:
            raise AttributeError()


class DeploymentSource(DeploymentAsset):
    def __init__(self, asset_type=None):
        DeploymentAsset.__init__(self, asset_type)


class DeploymentDestination(DeploymentAsset):
    def __init__(self, asset_type=None):
        DeploymentAsset.__init__(self, asset_type)


class DeploymentMap(object):
    def __init__(self, source=None, destination=None):
        self.source = source
        self.destination = destination


class ManagedDeployment(Deployment):

    @staticmethod
    def list(project=None, archive=False):
        deployments = []
        return deployments

    @staticmethod
    def create(deployment=None):
        server = deployment.project.server

        try:
            server.exists(deployment.path)
        except AlreadyExistsError, e:
            Utils.notice("Deployment already exists, updating")

        if not deployment.validate():
            raise ValidationError("There was a problem initializing the deployment")

        return deployment

    @staticmethod
    def load(search_path, project):
        root_path = re.sub(r'(.*/deployments/[^/]+)/.*', r'\1', search_path)
        name = re.sub(r'.*/deployments/([^/]+)$', r'\1', root_path)
        return Deployment(project, name, code=None, database=None, files=None)

    def __str__(self):
        return "Deployment {0}".format(self.name)

    def __init__(self, project=None, name=None):
        Deployment.__init__(self, project, "managed", name)


class ExternalDeployment(Deployment):

    def __init__(self, project=None):
        Deployment.__init__(self, project, "external", "unknown")
        self.drupal_site = DrupalSite(self.server, self.project.external_path)


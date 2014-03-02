import os
import string
import random
from datetime import datetime
from fabric.api import *
from fabric.utils import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.files import exists
from druploy.utils import *
from druploy.deployment import *

class Database(object):
    def __init__(self, deployment):
        self.deployment = deployment
        self.server = self.deployment.server

    def export(self, tag, path):
        filename = self.uid(tag) + ".sql"
        filepath = join(path, filename)
        self.deployment.drupal_site.drush.sql_dump(filepath)
        return filepath

    def uid(self, tag):
        return Asset.parse_uid(self.generate_parameters(tag))

    def generate_parameters(self, tag):
        self.settings = self.deployment.drupal_site.database_settings()
        parameters = {
            "host": self.server.hostname(),
            "branch": self.deployment.drupal_site.branch(),
            "revision": self.deployment.drupal_site.revision(),
            "timestamp": Asset.timestamp(),
            "deployment_type": self.deployment.deployment_type,
            "project": self.deployment.project.name,
            "deployment": self.deployment.name,
            "tag": tag,
            "asset_type": "database"
        }
        return parameters

    def prepare_database(self):
        site_directory = self.deployment.drupal_site.path.sites.default
        with settings(**self.server.settings()):
            settings_php = join(site_directory, 'settings.php')
            if not self.server.exists(settings_php):
                self.server.copy(join(site_directory, 'default.settings.php'), settings_php)

            self.server.append(settings_php, "@include('settings.local.php');");

            settings_local_php = join(site_directory, 'settings.local.php')
            if not self.server.exists(settings_local_php):
                context = self.generate_settings()
                upload_template('settings.local.php', settings_local_php, context, True, env.template_dir, False, True, mode=0666)

            self.deployment.drupal_site.drush.sql_create()


    def generate_settings(self):
        settings = {
            "host": "127.0.0.1",
            "name": self.generate_name(),
            "username": self.deployment.project.name,
            "password": ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
        }
        return settings

    def generate_name(self):
        parameters = {
            "prefix": "ap",
            "project": self.deployment.project.name,
            "deployment": self.deployment.name,
            "revision_or_branch": self.deployment.code.source.revision_or_branch
        }
        return "{prefix}_{project}_{deployment}_{revision_or_branch}".format(**parameters)


class DatabaseDeploymentSource(Database, DeploymentSource):
    def __init__(self, deployment=None):
        Database.__init__(self, deployment)
        DeploymentSource.__init__(self, 'database')
        self.path = Path(self.server, str(self.deployment.path), 'database')
        self.assets = AssetStore(self.server, str(self.path.source), ['database'])

    def snapshot(self):
        filepath = self.export('source', self.path.source)
        return Asset(self.server, filepath)


class UpdateFromServerDeploymentDatabaseSource(DatabaseDeploymentSource):
    def __str__(self):
        return "Update From Server Source"

    def __init__(self, deployment):
        DatabaseDeploymentSource.__init__(self, deployment)

    def collect(self, destination):
        self.asset = self.snapshot()

    def send(self, destination):
        self.server.transfer(self.asset.path, destination.server, destination.path.source)


class ResetToSnapshotDeploymentDatabaseSource(DatabaseDeploymentSource):
    def __str__(self):
        return "Update From Server Source"

    def __init__(self, deployment):
        DatabaseDeploymentSource.__init__(self, deployment)

    def collect(self, destination):
        try:
            self.asset = self.assets.match(self.generate_parameters('source'), ignore=['timestamp', 'revision']).list()[0]
        except IndexError, e:
            self.asset = self.snapshot()

    def send(self, destination):
        try:
            destination.assets.match(self.generate_parameters('source'), ignore=['timestamp', 'revision']).list()[0]
        except IndexError, e:
            self.server.transfer(self.asset.path, destination.server, destination.path.source)


class DatabaseDeploymentDestination(Database, DeploymentDestination):
    def __str__(self):
        return "Load into database Destination"

    def __init__(self, deployment):
        Database.__init__(self, deployment)
        DeploymentDestination.__init__(self, "database")
        self.path = Path(self.server, str(self.deployment.path), 'database')
        self.assets = AssetStore(self.server, str(self.path), ['database'])

    def pre_deploy(self, source):
        return
        if not self.exists():
            self.create()
            self.snapshot("pre-deploy")
        else:
            self.snapshot("pre-deploy")
            self.drop_tables()

    def deploy(self, source):
        self.prepare_database()
        self.destination_filepath = join(self.path.source, source.asset.filename)
        self.deployment.drupal_site.drush.sql_import(self.destination_filepath)

    def post_deploy(self, source):
        return
        self.snapshot("post-deploy")


class DrupalInstallDatabaseSource(Database, DeploymentSource):
    def __init__(self):
        Database.__init__(self, deployment)
        DeploymentSource.__init__(self, "database")

    def prepare(self, destination):
        destination.drupal_site.drush.sql_create(destination.database.db_url())

    def deploy(self, destination):
        destination.deployment.drupal_site.drush.site_install(profile="standard", db_url=self.db_url())


class MySQLDatabaseServer:
    def __init__(self, su='root', su_password=None, user='user', password=None):
        self.su = su
        self.su_password = su_password
        self.user = user
        self.password = password

    def __admin_connection(self):
        connection = "mysqladmin -u %s" % self.su
        if self.su_password is not None:
            connection = connection + " -p%s" % self.su_password
        return connection + " "

    def __connection(self, su=False):
        user = self.user
        password = None
        if su is True:
            user = self.su
        if su is True and self.su_password is not None:
            password = self.su_password
        if su is False and self.password is not None:
            password = self.password

        connection = "mysql -u %s" % user
        if password is not None:
            connection = connection + " -p%s" % password
        return connection + " "

    def exists(self, deployment):
        with settings(hide('warnings'), warn_only=True):
            if 'Unknown database' in run(self.__connection() + "-e 'use %s'" % self.db_name(deployment), quiet=True):
                return False
            return True

    def create(self, deployment):
        run(self.__admin_connection() + "create %s" % self.db_name(deployment))

    def delete(self, deployment):
        run(self.__admin_connection() + "drop %" % self.db_name(deployment))

    def db_name(self, deployment):
        return deployment.uid('_')



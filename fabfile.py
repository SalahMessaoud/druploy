import yaml
from fabric.api import *
from fabric.context_managers import *
from fabric.operations import *
from fabric.contrib.files import *
from fabric.contrib.console import *

from druploy.core import *
from druploy.utils import *
from druploy.exceptions import *
from druploy.server import *
from druploy.project import *
from druploy.deployment import *
from druploy.drupal import *
from druploy.code import *
from druploy.database import *
from druploy.files import *
from druploy.domain import *

env.forward_agent = True

env.local_path = os.path.dirname(os.path.realpath(__file__))
env.template_dir = os.path.join(env.local_path, "templates")

# Initialization
env.server = None
env.project = None

env.source_project = None
env.source_deployment = None
env.source_code = None
env.source_files = None
env.source_database = None

env.deployment = None
env.domain = None

@runs_once
def init():
    try:
        #env.clean = 'running', 'stdout', 'stderr'
        env.clean = ()

    except AgileProjectError, e:
        puts("There was a problem initializing the task, execution failed")
        raise


def server(name=None):
    config = Utils.load('servers.yaml', name)
    env.hosts = [config['host']]
    env.host_string = config['host']
    env.user = config['user']
    env.group = config['group']
    env.alias = name
    env.server = Server(name, config['host'], config['user'], config['group'])
    env.database_server = MySQLDatabaseServer(su=config['mysql']['su'], su_password=config['mysql']['supassword'], user=config['mysql']['user'], password=config['mysql']['password'])


def project(name=None):
    execute(init)
    try:
        env.project = ManagedProject(env.server, name)
        if not env.project.exists():
            if confirm("The project {0} does not exist, would you like to create it?".format(env.project.name)):
                Project.create(env.project)
            else:
                Utils.error("Cannot perform tasks on non existing project")
                abort("Aborting")
    except AgileProjectError, e:
        Utils.error("Could not create project, ending")


def project_create(name=None):
    execute(init)
    try:
        Project.create(Project(name, env.server))
    except AgileProjectError, e:
        puts("Could not create project, ending")


def project_list(archive=False):
    execute(init)
    try:
        with hide(*env.clean):
            Utils.notice("The server has the following projects")
            map(lambda notices: Utils.notice(notices, 4), Project.list(env.server, archive))
    except AgileProjectError, e:
        Utils.error("Could not list projects, ending")


def deployment_list(project=None):
    execute(init)
    try:
        with hide(*env.clean):
            if project is None:
                env.project = Project(name, env.server)
            Utils.notice("The project {0} has the following deployments".format(env.project.name))
            map(lambda notices: Utils.notice(notices, 4), Deployment.list(env.project))
    except AgileProjectError, e:
        Utils.error("Could not list deployments, ending")
        raise


def source(drupal_root=None):
    execute(init)
    try:
        with hide(*env.clean):
            env.source_project = ExternalProject(env.server, drupal_root)
            env.source_deployment = ExternalDeployment(env.source_project)
    except AgileProjectError, e:
        Utils.error("Could not initialize an unmanaged source deployment")
        raise


def code(url=None, branch='master', revision=None):
    execute(init)
    try:
        with hide(*env.clean):
            env.source_code = CodeDeploymentSource(env.source_deployment, url, branch, revision)
    except AgileProjectError, e:
        Utils.error("Could not configure code, ending")
        raise


def database(updating=True, resetting=False, installing=False):
    execute(init)
    try:
        with hide(*env.clean):
            if updating == 'True':
                env.source_database = UpdateFromServerDeploymentDatabaseSource(env.source_deployment)
            elif resetting == 'True':
                env.source_database = ResetToSnapshotDeploymentDatabaseSource(env.source_deployment)
            elif installing == 'True':
                env.source_database = DrupalInstallDeploymentDatabaseSource()
    except AttributeError, e:
        Utils.error("Source deployment not initialized properly, could not collect database")
    except AgileProjectError, e:
        Utils.error("Could not collect database")
        abort("Ending")


def files(updating=True, resetting=False):
    execute(init)
    try:
        with hide(*env.clean):
            if updating == 'True':
                env.source_files = UpdateFromServerFilesSource(env.source_deployment)
            elif resetting == 'True':
                env.source_files = ResetToSnapshotFilesSource(env.source_deployment)
    except AttributeError, e:
        Utils.error("Source deployment not initialized properly, could not collect files")
    except AgileProjectError, e:
        Utils.error("Could not collect files")
        abort("Ending")


def deploy(name=None):
    execute(init)
    try:
        with hide(*env.clean):
            env.deployment = ManagedDeployment(env.project, name)
            ManagedDeployment.create(env.deployment)

            env.deployment.code.source = env.source_code
            env.deployment.code.destination = CodeDeploymentDestination(env.deployment)
            env.deployment.files.source = env.source_files
            env.deployment.files.destination = FilesDestination(env.deployment)
            env.deployment.database.source = env.source_database
            env.deployment.database.destination = DatabaseDeploymentDestination(env.deployment)

            env.deployment.run()

    except AgileProjectError, e:
        Utils.error("Could not deploy, ending")
        raise


def domain(name=None, aliases=[]):
    execute(init)
    try:
        with hide(*env.clean):
            env.domain = Domain(env.deployment, name, aliases)
            env.domain.create()
            env.domain.enable()
    except AttributeError, e:
        Utils.error("Source deployment not initialized properly, could not enable")
    except AgileProjectError, e:
        Utils.error("Could not enable domain")
        abort("Ending")


def drush_alias_create():
    execute(init)
    try:
        with hide(*env.clean):
            drupal_roots = DrupalRoot.list(env.project)

            Utils.notice("The project has the following Drupal roots")
            [Utils.notice(drupal_root, 4) for drupal_root in drupal_roots]

            Utils.notice("Creating Drush aliases")
            for drupal_root in drupal_roots:
                drush_alias = DrushAlias(drupal_root)
                DrushAlias.create(drush_alias)

    except AgileProjectError, e:
        Utils.error("Could not sync aliases")
        raise



'''
def update_db():
def update_files():
def backup_code():
def backup_db():
def backup_files():

def drush_alias():
    for project in env.aps.projects():
        for deployment in project.deployments():
            drush.create_alias(deployment)


def drush_remote_alias():
    env.aps = Server('/var/www/ap', env.host_string)
    for project in env.aps.projects():
        for deployment in project.deployments():
            with settings(host_string='localhost'):
                drush.create_alias(deployment)


'''

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


@task
def server(name=None):
    """
        Set the current server
    """
    config = Utils.load(os.path.join(env.local_path, 'servers.yaml'), name)
    env.hosts = [config['host']]
    env.host_string = config['host']
    env.user = config['user']
    env.group = config['group']
    env.alias = name
    env.server = Server(name, config['host'], config['user'], config['group'])
    env.database_server = MySQLDatabaseServer(su=config['mysql']['su'], su_password=config['mysql']['supassword'], user=config['mysql']['user'], password=config['mysql']['password'])


@task
def project(name=None):
    """
    Set the current project for Druploy
    """
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


@task
def project_create(name=None):
    """
    Create a project on a server
    """
    execute(init)
    try:
        Project.create(Project(name, env.server))
    except AgileProjectError, e:
        puts("Could not create project, ending")


@task
def project_list(archive=False):
    """
    List all projects on a server
    """
    execute(init)
    try:
        with hide(*env.clean):
            Utils.notice("The server has the following projects")
            map(lambda notices: Utils.notice(notices, 4), Project.list(env.server, archive))
    except AgileProjectError, e:
        Utils.error("Could not list projects, ending")


@task
def deployment_list(project=None):
    """
    List all deployments for a project (optional) on a server
    """
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


@task
def source(drupal_root=None):
    """
    When taking the database/files from a project not managed by Druploy, tell it
    where the drupal root is
    """
    execute(init)
    try:
        with hide(*env.clean):
            env.source_project = ExternalProject(env.server, drupal_root)
            env.source_deployment = ExternalDeployment(env.source_project)
    except AgileProjectError, e:
        Utils.error("Could not initialize an unmanaged source deployment")
        raise


@task
def code(url=None, branch='master', revision=None):
    """
    Tell Druploy where to get the code and what branch/revision to deploy
    """
    execute(init)
    try:
        with hide(*env.clean):
            env.source_code = CodeDeploymentSource(env.source_deployment, url, branch, revision)
    except AgileProjectError, e:
        Utils.error("Could not configure code, ending")
        raise


@task
def database(updating=True, resetting=False, installing=False):
    """
    Tell Druploy what method to use to deploy the database
    """
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


@task
def files(updating=True, resetting=False):
    """
    Tell Druploy what method to use to deploy the files
    """
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


@task
def deploy(name=None):
    """
    Run the deployment on the configured code, files and database
    """
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


@task
def domain(name=None, aliases=[]):
    """
    Configure a domain to run on the current deployment
    """
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


@task
def drush_alias_create():
    """
    Create drush aliases for each deployment in each project
    """
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



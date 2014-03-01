from fabric.api import *
from fabric.utils import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.files import exists
from datetime import datetime
import os
from druploy.utils import *

class Project(object):

    folders = [
        "wcs",
        "deployments",
        "code",
        "databases",
        "files"
    ]

    @staticmethod
    def list(server=None, arhive=False):
        raise TypeError("{0} projects cannot be listed".format(self.project_type))

    @staticmethod
    def create(project=None):
        raise TypeError("{0} projects cannot be created".format(self.project_type))

    @staticmethod
    def load(name=None):
        raise TypeError("{0} projects cannot be loaded".format(self.project_type))

    def __str__(self):
         return "{0} project running on {1} named {2}".format(self.project_type, self.server.host, self.name)

    def __init__(self, server=None, project_type=None, name=None):
        if server is None:
            raise ValueError("You must provide a server")
        self.server = server

        if name is None:
            raise ValueError("You must specify a project name")
        self.name = name

        self.project_type = project_type

    def exists(self):
        return self.server.exists(self.path)

    def delete(self, prompt=True):
        raise TypeError("{0} projects cannot be deleted".format(self.project_type))

    def archive(self, prompt=True):
        raise TypeErrror("{0} projects cannot be archived".format(self.project_type))

    def validate(self):
        return True

    def validated(self):
        return True


class ExternalProject(Project):

    def __init__(self, server=None, external_path=None):
        Project.__init__(self, server, "unknown", "external")
        self.path = Path(server, server.path, "projects", "external", "unknown")
        self.external_path = external_path

        if not self.exists():
            raise ValueError("You must specify a valid root path")


class ManagedProject(Project):

    @staticmethod
    def list(server=None, archive=False):
        projects = []
        with settings(host_string = server.host):
            path = server.active_path if archive is False else server.archive_path
            with cd(path):
                for name in run("find . -maxdepth 1 -mindepth 1 -type d -exec basename {} \;").split():
                    projects.append(Project(name, server))
        return projects

    @staticmethod
    def create(project=None):
        with settings(host_string=project.server.host):
            with cd(project.server.active_path):
                try:
                    project.server.mkdir(project.name)
                except AlreadyExistsError, e:
                    raise AlreadyExistsError("Project already exists")

            with cd(project.root_path):
                map(lambda mkdirs: project.server.mkdir(mkdirs), Project.folders);

            if not project.validate():
                raise ValidationError("There was a problem creating the project")

            return project
    def __init__(self, server=None, name=None):
        Project.__init__(self, server, "managed", name)
        self.path = Path(server, server.path.__str__(), "managed", "available", name)

    def delete(self, prompt=True):
        # For now we don't do dangerous stuff like deletes
        return archive(prompt)

    def archive(self, prompt=True):
        if prompt is True:
            if confirm("Are you sure you want to archive the project?", default=False):
                self.server.mv(self.root_path, self.archive_path)

    def exists(self):
        with settings(**self.server.settings()):
            return exists(self.path)



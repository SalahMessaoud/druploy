from datetime import datetime
import os
from fabric.api import *
from fabric.utils import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.files import *
from druploy.exceptions import *

class Server:
    def __init__(self, alias=None, host=None, user=None, group=None, root_path='/var/www/ap'):
        self.path = root_path
        self.alias = alias if alias is not None else env.alias
        self.host = host if host is not None else env.host_string
        self.user = user if user is not None else env.user
        self.group = group if group is not None else env.group

        with settings(**self.settings()):
            if not exists(self.path):
                self.mkdir(self.path, user=self.user, group=self.group, permissions=755, do_sudo=True)

    def mkdirs(self, dirs=[]):
        map(lambda mkdirs: self.mkdir(mkdirs), dirs);

    def mkdir(self, directory=None, user=None, group=None, permissions=None, do_sudo=False):
        if not directory:
            raise ValueError("Invalid directory name")

        with settings(**self.settings()):
            if exists(directory):
                raise AlreadyExistsError("Folder already exists")

            self.sudo_or_run("mkdir -p %s" % directory, do_sudo)
            if user and group:
                self.sudo_or_run("chown %s:%s %s" % (user, group, directory), do_sudo)
            if permissions:
                self.sudo_or_run("chmod %s %s" % (permissions, directory), do_sudo)

    def symlink(self, directory=None, link=None, sudo=False):
        if not directory or not link:
            raise ValueError("You must specify both a directory and a link")
        if not exists(directory):
            raise ValueError("The directory you are trying to link to does not exist")

        self.sudo_or_run("ln -s {0} {1}".format(directory, link), sudo)

    def sudo_or_run(self, command, do_sudo=False):
        if do_sudo is True:
            return sudo(command)
        else:
            return run(command)

    def sudo(self, command):
        with settings(**self.settings()):
            sudo(command)

    def settings(self):
        return {
            "host_string": self.host,
            "user": self.user,
            "group": self.group
        }

    def exists(self, path):
        with settings(**self.settings()):
            return exists(path)

    def append(self, filepath, text):
        with settings(**self.settings()):
            append(filepath, text, use_sudo=False, escape=True)

    def copy(self, from_path, to_path, user=None, group=None, permissions=None, do_sudo=False):
        with settings(**self.settings()):
            self.sudo_or_run("cp -rp {0} {1}".format(from_path, to_path), do_sudo)
            if user and group:
                self.chown(to_path, user, group)
            if permissions:
                self.chmod(to_path, permissions)

    def rmfile(self, filepath, do_sudo=False):
        if self.exists(filepath):
            with settings(**self.settings()):
                self.sudo_or_run("rm {0}".format(filepath), do_sudo)

    def chown(self, path, user, group, recursive=False, do_sudo=False):
        with settings(**self.settings()):
            command = "chown"
            if recursive is True:
                command += " -R"
            return self.sudo_or_run(command + " {0}:{1} {2}".format(user, group, path), do_sudo)

    def chmod(self, path, permissions, recursive=False, do_sudo=False):
        with settings(**self.settings()):
            command = "chmod"
            if recursive is True:
                command += " -R"
            return self.sudo_or_run(command + " {0} {1}".format(permissions, path), do_sudo)

    def hostname(self):
        with settings(**self.settings()):
            return run("hostname")

    def transfer(self, source_path, destination_server, destination_path):
        with settings(**self.settings()):
            params = {
                "source": source_path,
                "user": destination_server.user,
                "host": destination_server.host,
                "destination": destination_path
            }
            run("rsync -avz --progress {source} {user}@{host}:{destination}".format(**params))


class UbuntuServer:
    def __init__(self):
            self.data = []

    def ensure_vhost_exists(self, domain):
        local('echo hello')
        require('domain')
        exists('/etc/apache2/sites-available/$(domain).conf', verbose=True)



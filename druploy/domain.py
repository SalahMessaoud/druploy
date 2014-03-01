import os
from os.path import join
from fabric.api import *
from fabric.utils import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.files import *
from druploy.exceptions import *

class Domain(object):

    @staticmethod
    def list():
        pass

    def __init__(self, deployment, name, aliases=[]):
        self.deployment = deployment
        self.server = self.deployment.server
        self.aliases = aliases
        self.name = name
        self.full_name = "{0}.{1}.{2}".format(self.deployment.project.name, self.deployment.name, self.name)

    def create(self):
        with settings(**self.server.settings()):
            filepath = join(self.deployment.path.domain, self.name)
            context = {
                "name": self.name,
                "full_name": self.full_name,
                "aliases": self.aliases,
                "document_root": self.deployment.drupal_site.path
            }
            upload_template('vhost.conf', filepath, context, True, env.template_dir, False, True, mode=0644)
            self.server.symlink(filepath, join('/etc/apache2/sites-available', self.full_name), sudo=True)

    def delete(self):
        pass

    def enable(self):
        self.server.sudo("a2ensite {0}".format(self.full_name))
        self.server.sudo("service apache2 reload")

    def disable(self):
        self.server.sudo("a2dissite {0}".format(self.full_name))
        self.server.sudo("service apache2 reload")



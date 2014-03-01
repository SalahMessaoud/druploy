import re
import os
from datetime import datetime
from fabric.operations import *
from fabric.api import *
from fabric.utils import *
from fabric.context_managers import *
from fabric.contrib.files import *
from druploy.exceptions import *
from druploy.git import *
from druploy.utils import *

class DrupalRoot(object):

    @staticmethod
    def list(project):
        with cd(project.path):
            settings_files = run("find $PWD -regex '.*sites/default/default.settings.php'").split()
            drupal_roots = []
            for settings_file in settings_files:
                root_path = re.sub(r'(.*)(.*/sites/default/default.settings.php)', r'\1', settings_file)
                drupal_roots.append(DrupalRoot(Deployment.load(root_path, project), root_path))
        return drupal_roots

    def __str__(self):
        return "Drupal root {0} running inside project {1}".format(self.path, self.project.name)

    def __init__(self, deployment, root_path):
        self.deployment = deployment
        self.project = self.deployment.project
        self.server = self.project.server
        self.path = root_path

    def sites(self):
        return ['default']

    def validate(self):
        pass


class DrupalSite(GitWorkingCopy):

    @staticmethod
    def find(server, base_path):
        drupal_sites = []
        with settings(**server.settings()):
            with cd(base_path):
                settings_files = run("find $PWD -regex '.*sites/default/default.settings.php'").split()
                for settings_file in settings_files:
                    drupal_site_path = re.sub(r'(.*)(.*/sites/default/default.settings.php)', r'\1', settings_file)
                    drupal_sites.append(DrupalSite(server, drupal_site_path))
        return drupal_sites


    def __init__(self, server=None, root_path=None):
        GitWorkingCopy.__init__(self, root_path)
        self.server = server
        self.drush = Drush(self.server, root_path)
        self.path = Path(self.server, root_path)

    def name(self):
        return self.drush.variable_get('site_name')

    def db(self):
        return self.drush.sql_connect()

    def validate(self):
        with cd(self.path):
            with cd('../../'):
                if exists('CHANGELOG.txt'):
                    return True
        return False

    def database_settings(self):
        return self.drush.sql_connect()


class Drush(object):
    def __init__(self, server=None, path=None):
        self.server = server
        self.path = path

    def execute(self, command):
        with settings(**self.server.settings()):
            with cd(self.path):
                return run("drush -y {0}".format(command))

    def variable_get(self, name):
        with settings(**self.server.settings()):
            with cd(self.path):
                result = self.execute("vget {0} --exact".format(name))
                result = re.sub(re.compile("{0}:\s+'([^']+)'".format(name), re.MULTILINE), r'\1', result)
                return result

    def sql_connect(self):
        with settings(**self.server.settings()):
            with cd(self.path):
                puts("PATH: " + self.path)
                result = self.execute("sql-connect")
                matches = re.compile("mysql --database=(?P<name>.+) --host=(?P<host>.+) --user=(?P<user>.+) --password=(?P<password>.+)", re.MULTILINE).match(result)
                if matches is None:
                    return {
                        "name": None,
                        "host": None,
                        "user": None,
                        "password": None
                    }
                else:
                    return matches.groupdict()

    def sql_dump(self, filepath):
        with settings(**self.server.settings()):
            with cd(self.path):
                self.execute("sql-dump > {0}".format(filepath))
                return True

    def sql_import(self, filepath):
        with settings(**self.server.settings()):
            with cd(self.path):
                self.execute("sql-cli < {0}".format(filepath))
                return True

    def sql_create(self):
        with settings(**self.server.settings()):
            with cd(self.path):
                self.execute("sql-create --db-su={0} --db-su-pw={1}".format(env.database_server.su, env.database_server.su_password))
                return True

class DrushAlias(object):

    @staticmethod
    def __create(drush_alias, alias_context):
        server = drush_alias.server
        # Initialize if this is the first time aliases are run on this project/server
        alias_dir = os.path.join(server.path.__str__(), 'aliases')
        if not exists(alias_dir):
            server.mkdir(alias_dir, user=env.user, group=env.group, permissions=755, do_sudo=True)

        all_file_path = os.path.join(alias_dir, drush_alias.project.name + '.aliases.drushrc.php')
        if not exists(all_file_path):
            upload_template('project-all.aliases.drushrc.php', destination=all_file_path, context=alias_context, use_jinja=True, template_dir=env.template_dir, use_sudo=False, backup=False, mode=0644)

        if not exists(os.path.dirname(drush_alias.file_path)):
            server.mkdir(os.path.dirname(drush_alias.file_path), user=env.user, group=env.group, permissions=755, do_sudo=True)

        upload_template('project-host.aliases.drushrc.php', destination=drush_alias.file_path, context=alias_context, use_jinja=True, template_dir=env.template_dir, use_sudo=False, backup=False, mode=0644)

    @staticmethod
    def create(drush_alias):
        drupal_root = drush_alias.drupal_root
        project = drupal_root.project
        server = project.server

        DrushAlias.__create(drush_alias, drush_alias.context())
        with settings(**server.settings_local()):
            DrushAlias.__create(drush_alias, drush_alias.context())

        if not drush_alias.validate():
            raise ValidationError("There was a problem creating the alias")

        return drush_alias

    @staticmethod
    def load(name=None):
        pass

    def __str__(self):
         return self.name

    def __init__(self, drupal_root):
        self.drupal_root = drupal_root
        self.deployment = self.drupal_root.deployment
        self.project = self.deployment.project
        self.server = self.project.server

        self.aliases_dir = os.path.join(self.server.path.__str__(), 'aliases', env.host_string)
        self.file_path = os.path.join(self.aliases_dir, self.project.name + '.' + self.deployment.name + '.aliases.drushrc.php')

    def context(self):
        context = {
            'server_alias': self.server.alias,
            'deployment': self.deployment.name,
            'root': self.drupal_root.path.__str__(),
            'site': 'default'
        }
        if env.host_string is 'localhost':
            context['remote_user'] = self.server.user
            context['remote_host'] = self.server.host
        return context

    def validate(self):
        return True



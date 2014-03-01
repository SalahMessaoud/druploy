from datetime import *
from time import *
from os.path import join
import yaml
import re
import operator
from fabric.api import *
from fabric.utils import *
from fabric.colors import *
from fabric.context_managers import *
from fabric.contrib.files import exists
from exceptions import *


class Path(object):
    def __init__(self, server, *args):
        self.server = server
        self.root = join(*args)
        self.__mkdir(self.root)

    def __str__(self):
        return self.root

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(self)

    def __getattr__(self, name):
        path = Path(self.server, self.root, name)
        self.__mkdir(path)
        return path

    def __mkdir(self, path):
        if not self.server.exists(path):
            self.server.mkdir(path)

    def replace(self, old, new, *args):
        return self.root.replace(old, new, *args)

    def endswith(self, suffix, start=None, end=None):
        return self.root.endswith(suffix, start, end)


class Utils:

    @staticmethod
    def notice(text="", shift=0):
        return puts(indent(green(text), shift))

    @staticmethod
    def error(text="", shift=0):
        return puts(indent(red(text), shift))

    @staticmethod
    def timestamp():
        return strftime("%Y-%m-%dT%H-%M-%S+0000", gmtime());

    @staticmethod
    def load(filename, element):
        f = open(filename)
        config = yaml.safe_load(f)[element]
        f.close()
        return config


class AssetParseError(AgileProjectError):
    pass


class Asset(object):
    DATE_FORMAT = "%Y-%m-%dT%H-%M-%S+0000"
    REGEX = re.compile("^(?P<asset_type>.*)--(?P<host>.*)--(?P<branch>.*)--(?P<revision>.*)--(?P<timestamp>.*)--(?P<deployment_type>.*)--(?P<project>.*)--(?P<deployment>.*)--(?P<tag>.*)$")
    FILETYPE = re.compile("^(.+)(\.[\d\w]{3,4})$")

    @staticmethod
    def timestamp():
        return strftime(Asset.DATE_FORMAT, gmtime());

    @staticmethod
    def parse_parameters(uid):
        match = Asset.REGEX.match(uid)
        if match is not None:
            return match.groupdict()
        return None

    @staticmethod
    def parse_uid(parameters):
        return "{asset_type}--{host}--{branch}--{revision}--{timestamp}--{deployment_type}--{project}--{deployment}--{tag}".format(**parameters)

    def __str__(self):
        return self.uid

    def __init__(self, server=None, filepath=None):
        self.server = server
        self.path = Path(self.server, filepath)
        self.filepath = filepath
        self.filename = os.path.basename(self.filepath)

        match = Asset.FILETYPE.match(self.filename)
        if match is not None:
            groups = match.groups()
            self.uid = groups[0]
            self.filetype = groups[1]
        else:
            self.uid = self.filename
            self.filetype = 'dir'

        self.asset_type = None
        self.host = None
        self.branch = None
        self.revision = None
        self.timestamp = None
        self.deployment_type = None
        self.project = None
        self.deployment = None
        self.tag = None

        data = Asset.parse_parameters(self.uid)
        if data is not None:
            self.asset_type = data['asset_type']
            self.host = data['host']
            self.branch = data['branch']
            self.revision = data['revision']
            self.timestamp = strptime(data['timestamp'], Asset.DATE_FORMAT)
            self.deployment_type = data['deployment_type']
            self.project = data['project']
            self.deployment = data['deployment']
            self.tag = data['tag']
        else:
            raise AssetParseError

    def parameters(self):
        return Asset.parse_parameters(self.uid)


class AssetStore(object):
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '>=': operator.ge,
        '<=': operator.le,
    }

    def __init__(self, server, root_path, asset_types=['database', 'files'], max_depth=3, assets=None):
        self.server = server
        self.root_path = root_path
        self.asset_types = asset_types
        self.max_depth = max_depth
        self.assets = assets

    def load(self):
        self.assets = []
        with settings(**self.server.settings()):
            command = "find {0} -maxdepth {1}".format(self.root_path, self.max_depth)
            for i, asset_type in enumerate(self.asset_types):
                if i is not 0:
                    command += " -or"
                command += " -regex .*/{0}--.*".format(asset_type)
            for filepath in run(command).split():
                try:
                    asset = Asset(self.server, filepath)
                    self.assets.append(asset)
                except AssetParseError, e:
                    #The regex didn't match
                    pass

    def match(self, parameters, ignore=[]):
        store = self
        for key, value in parameters.iteritems():
            if key not in ignore:
                store = store.filter(key, '==', value)
        return store

    def filter(self, field, operator, value):
        if self.assets is None:
            self.load()

        filtered = [asset for asset in self.assets if self._test(getattr(asset, field), value, AssetStore.OPERATORS[operator])]
        return AssetStore(self.server, self.root_path, self.asset_types, self.max_depth, filtered)

    def sort(self, sorts):
        if isinstance(sorts, basestring): sorts = [sorts]

        if self.assets is None:
            self.load()
        return multikeysort(self.assets, sorts)

    def list(self):
        if self.assets is None:
            self.load()
        return self.assets

    def _test(self, a, b, operator):
        return operator(a, b)


def multikeysort(items, columns, functions={}, getter=operator.attrgetter):
    """Sort a list of dictionary objects or objects by multiple keys bidirectionally.
    Keyword Arguments:
        items -- A list of dictionary objects or objects
        columns -- A list of column names to sort by. Use -column to sort in descending order
        functions -- A Dictionary of Column Name -> Functions to normalize or process each column value
        getter -- Default "getter" if column function does not exist
                    operator.itemgetter for Dictionaries
                    operator.attrgetter for Objects
    """
    comparers = []
    for col in columns:
        column = col[1:] if col.startswith('-') else col
        if not column in functions:
            functions[column] = getter(column)
        comparers.append((functions[column], 1 if column == col else -1))

    def comparer(left, right):
        for func, polarity in comparers:
            result = cmp(func(left), func(right))
            if result:
                return polarity * result
        else:
            return 0
    return sorted(items, cmp=comparer)

    def compose(inner_func, *outer_funcs):
        """Compose multiple unary functions together into a single unary function"""
        if not outer_funcs:
            return inner_func
        outer_func = compose(*outer_funcs)
        return lambda *args, **kwargs: outer_func(inner_func(*args, **kwargs))


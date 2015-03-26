"""

The Dataplicity Service


"""
from __future__ import unicode_literals
from __future__ import print_function


import glob
import os
import subprocess
import logging

from dataplicity.client import settings


class Project(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path


class Service(object):
    """Manages a number of dataplicity daemons"""

    def __init__(self):
        self.home_dir = os.environ.get('DATAPLICITY_HOME', '/etc/dataplicity/')
        self._conf = None
        self.load_conf()

    def __repr__(self):
        return "<dataplicity-service '{}'>".format(self.conf_path)

    @property
    def conf(self):
        return self._conf

    @property
    def conf_path(self):
        conf_path = self.get_path('srv.conf')
        return conf_path

    def get_path(self, path):
        return os.path.join(self.home_dir, path)

    def init_logging(self, name="logging.ini"):
        logging_path = self.get_path(name)
        logging.config.fileConfig(logging_path, disable_existing_loggers=True)

    def load_conf(self):
        self._conf = settings.read(self.conf_path)

        self.project_paths = project_paths = []
        for path in self.conf.get_list('projects', 'read'):
            for p in glob.glob(self.get_path(path)):
                project_paths.append(p)


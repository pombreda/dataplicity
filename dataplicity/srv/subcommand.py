from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.compat import with_metaclass
from dataplicity.srv import service


class SubCommandMeta(type):
    """Keeps a registry of sub-commands"""
    registry = {}

    def __new__(cls, name, base, attrs):
        new_class = type.__new__(cls, name, base, attrs)
        if name not in ("SubCommand", "SubCommandType"):
            cls.registry[name.lower()] = new_class
        return new_class


class SubCommandType(object):
    """Base class for sub-commands"""
    __metaclass__ = SubCommandMeta

    def __init__(self, app):
        self.app = app
        self._service = None
        super(SubCommandType, self).__init__()

    def add_arguments(self, parser):
        pass

    @property
    def service(self):
        if self._service is None:
            self._service = service.Service()
        return self._service

    def run(self):
        raise NotImplementedError


class SubCommand(with_metaclass(SubCommandMeta, SubCommandType)):
    pass

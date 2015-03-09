from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.compat import with_metaclass


class SubCommandMeta(type):
    """Keeps a registry of sub-commands"""
    registry = {}

    def __new__(cls, name, base, attrs):
        new_class = type.__new__(cls, name, base, attrs)
        if name != "SubCommand":
            cls.registry[name.lower()] = new_class
        return new_class


class SubCommandType(object):
    """Base class for sub-commands"""
    __metaclass__ = SubCommandMeta

    def __init__(self, app):
        self.app = app

    def add_arguments(self, parser):
        pass

    def run(self):
        raise NotImplementedError


class SubCommand(with_metaclass(SubCommandMeta, SubCommandType)):
    pass

from __future__ import unicode_literals
from __future__ import print_function

import argparse
import sys
import os
import logging
import logging.handlers
import logging.config

from dataplicity import __version__
from dataplicity.client import Client
from dataplicity.client import tools
from dataplicity.app.subcommand import SubCommandMeta
from dataplicity.app.subcommands import *


DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(name)s:%(levelname)s]: %(message)s",
            'datefmt': "[%d/%b/%Y %H:%M:%S]"
        },
    },
    'handlers': {

        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'dataplicity': {
            'handlers': ['syslog'],
            'level': logging.DEBUG,
            'propagate': True,
        },
    }
}


class ProjectNotFoundError(Exception):
    pass


class App(object):
    """Dataplicity device management"""

    def __init__(self):
        self._conf = None
        self.subcommands = {name: cls(self)
                            for name, cls in SubCommandMeta.registry.items()}

    def _get_argparser(self):
        parser = argparse.ArgumentParser("dataplicity",
                                         description=getattr(self, '__doc__', ''))
        parser.add_argument('-v', '--version', action="version", version=__version__,
                            help="Display version and exit")
        parser.add_argument('-d', '--debug', action="store_true", dest="debug", default=False,
                            help="Enables debug output")
        parser.add_argument('-c', '--conf', metavar="PATH", dest="conf", default=None,
                            help="the location of the conf file to load")
        parser.add_argument('-l', '--logging', metavar="PATH", dest="logging", default="/etc/dataplicity/logging.conf",
                            help="Location of logging conf file")
        parser.add_argument('-s', '--server-url', metavar="URL", dest="server_url", default=None,
                            help="URL of dataplicity.com api")

        subparsers = parser.add_subparsers(title='available sub-commands',
                                           dest="subcommand",
                                           help="sub-command help")

        for name, subcommand in self.subcommands.items():
            subparser = subparsers.add_parser(name,
                                              help=subcommand.help,
                                              description=getattr(subcommand, '__doc__', None))
            subcommand.add_arguments(subparser)

        return parser

    def init_logging(self, path=None, foreground=True):
        if path is not None and os.path.exists(path):
            logging.config.fileConfig(path)
        else:
            format = "%(asctime)s:%(name)s:%(levelname)s: %(message)s"
            datefmt = "[%d/%b/%Y %H:%M:%S]"

            if foreground:
                logging.basicConfig(format=format,
                                    datefmt=datefmt,
                                    level=logging.DEBUG)
            else:
                logging.config.dictConfig(DEFAULT_LOGGING)

    def make_client(self, log, conf=None, create_m2m=True):
        if self.args.conf:
            path = self.args.conf
        elif conf:
            path = conf
        else:
            path = tools.find_conf()
        if path is None:
            raise ProjectNotFoundError('unable to locate dataplicity.conf for project')
        client = Client(path, log=log, create_m2m=create_m2m)
        return client

    @property
    def conf(self):
        if self._conf is None:
            self._conf = self.args.conf or tools.find_conf()
            if self._conf is None:
                raise ProjectNotFoundError('unable to locate dataplicity.conf for project')
        return self._conf

    def run(self):
        parser = self._get_argparser()
        args = self.args = parser.parse_args(sys.argv[1:])
        self.init_logging(self.args.logging)

        subcommand = self.subcommands[args.subcommand]
        subcommand.args = args

        try:
            return subcommand.run() or 0
        except Exception as e:
            if self.args.debug:
                raise
            sys.stderr.write("(dataplicity {}) {}\n".format(__version__, e))
            cmd = sys.argv[0].rsplit('/', 1)[-1]
            debug_cmd = ' '.join([cmd, '--debug'] + sys.argv[1:])
            sys.stderr.write("(run '{}' for a full traceback)\n".format(debug_cmd))
            return -1

def run():
    app = App()
    sys.exit(app.run())

from __future__ import unicode_literals
from __future__ import print_function

import sys
import argparse

from dataplicity.srv import __version__
from dataplicity.srv.subcommand import SubCommandMeta
from dataplicity.srv.subcommands import *

class App(object):

    def __init__(self):
        self.subcommands = {name: cls(self)
                            for name, cls in SubCommandMeta.registry.items()}

    def _get_argparser(self):
        parser = argparse.ArgumentParser("dataplicity-srv",
                                         description="Dataplicity Service")

        parser.add_argument('-v', '--version', action="version", version=__version__,
                            help="Display version and exit")
        parser.add_argument('-d', '--debug', action="store_true", dest="debug", default=False,
                            help="Enables debug output")

        subparsers = parser.add_subparsers(title="available sub-commands",
                                           dest="subcommand",
                                           help="sub-command help")

        for name, subcommand in self.subcommands.items():
            subparser = subparsers.add_parser(name,
                                              help=subcommand.help,
                                              description=getattr(subcommand, '__doc__', None))
        return parser


    def run(self):
        parser = self._get_argparser()
        self.args = parser.parse_args(sys.argv[1:])

        subcommand = self.subcommands[self.args.subcommand]
        subcommand.args = self.args

        try:
            return subcommand.run() or 0
        except Exception as e:
            if self.args.debug:
                raise
            sys.stderr.write("(dataplicity-srv {}) {}\n".format(__version__, e))
            cmd = sys.argv[0].rsplit('/', 1)[-1]
            debug_cmd = ' '.join([cmd, '--debug'] + sys.argv[1:])
            sys.stderr.write("(run '{}' for a full traceback)\n".format(debug_cmd))
            return -1


def run():
    app = App()
    sys.exit(app.run())


from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.srv.subcommand import SubCommand
from dataplicity.srv.service import Service


class List(SubCommand):
    """List enabled projects"""
    help = "List enabled projects"

    def add_arguments(self, parser):
        pass


    def run(self):
        service = self.service
        print(service)
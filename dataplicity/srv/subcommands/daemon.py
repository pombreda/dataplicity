"""

Dataplicity service daemon

"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import sys
import os

from daemon import DaemonContext
from daemon.pidfile import TimeoutPIDLockFile

from dataplicity.srv import constants
from dataplicity.srv import comms
from dataplicity.srv import service
from dataplicity.srv.subcommand import SubCommand


class D(SubCommand):
    """Run a Dataplicity daemon process"""
    help = """Run the Dataplicity daemon"""

    @property
    def comms(self):
        return comms.Comms()

    def add_arguments(self, parser):
        parser.add_argument('-f', '--foreground', dest='foreground', action="store_true", default=False,
                            help="run daemon in foreground")
        parser.add_argument('-s', '--stop', dest="stop", action="store_true", default=False,
                            help="stop the daemon")
        parser.add_argument('-r', '--restart', dest='restart', action="store_true",
                            help="restart running daemon")
        parser.add_argument('-t', '--status', dest="status", action="store_true",
                            help="status of the daemon")
        parser.add_argument('-y', '--sync', dest="sync", action="store_true", default=False,
                            help="sync now")

    def make_daemon(self, debug=False):
        daemon = service.Daemon()
        return daemon

    # def get_conf(self):
    #     conf_path = self.args.conf or constants.CONF_PATH
    #     conf_path = abspath(conf_path)
    #     conf = settings.read(conf_path)
    #     return conf

    # def make_daemon(self, debug=None):
    #     conf_path = self.args.conf or constants.CONF_PATH
    #     conf_path = abspath(conf_path)

    #     conf = settings.read(conf_path)
    #     firmware_conf_path = conf.get('daemon', 'conf', conf_path)
    #     # It may not exist if there is no installed firmware
    #     if os.path.exists(firmware_conf_path):
    #         log.error("daemon firmware conf '{}' does not exist".format(firmware_conf_path))
    #         conf_path = firmware_conf_path

    #     if debug is None:
    #         debug = self.args.debug or self.args.foreground

    #     self.app.init_logging(self.app.args.logging,
    #                           foreground=self.args.foreground)
    #     dataplicity_daemon = Daemon(conf_path,
    #                                 foreground=self.args.foreground,
    #                                 debug=debug)
    #     return dataplicity_daemon

    def run(self):
        args = self.args

        if args.restart:
            return self.comms.restart() or 0

        if args.stop:
            return self.comms.stop()

        if args.sync:
            return self.comms.sync()

        if args.status:
            if self.comms.status():
                sys.stdout.write('running\n')
                return 0
            else:
                sys.stdout.write('not running\n')
                return 1

        try:
            if args.foreground:
                dataplicity_daemon = self.make_daemon()
                dataplicity_daemon.start()
            else:
                pid_path = os.environ.get('DATAPLICITY_SRV_PID', constants.DATAPLICITY_SRV_PID)
                if os.path.exists(pid_path):
                    sys.stderr.write('pid file "{}" exists. Is the Dataplicity service daemon already running?\n'.format(pid_path))
                    return -1
                daemon_context = DaemonContext(pidfile=TimeoutPIDLockFile(pid_path, 1))
                with daemon_context:
                    dataplicity_daemon = self.make_daemon()
                    dataplicity_daemon.start()

        except Exception as e:
            from traceback import print_exc
            print_exc(e)
            return -1

"""

The Dataplicity Service


"""
from __future__ import unicode_literals
from __future__ import print_function


import glob
import os
import time
import sys
from threading import Event
import logging
log = logging.getLogger('dataplicity-srv')

from dataplicity.client import settings
from dataplicity.srv import constants


class Project(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path

    def __repr__(self):
        return '<project "{}">'.format(self.name)


class Service(object):
    """Manages a number of dataplicity daemons"""

    def __init__(self):
        self.home_dir = os.environ.get('DATAPLICITY_HOME', constants.DATAPLICITY_HOME)
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


class Daemon(object):

    def __init__(self):
        self.pipe_path = constants.DATAPLICITY_SRV_PIPE
        self.exit_event = Event()
        self.poll_rate_seconds = 5
        self.exit_command = None

        global log
        log = logging.getLogger('dataplicity')

    def _make_pipe(self):
        try:
            os.mkfifo(self.pipe_path)
            log.debug("created named pipe '{}'".format(self.pipe_path))
        except:
            pass
            #log.exception('error creating pipe')

        try:
            pipe = os.open(self.pipe_path, os.O_RDONLY, os.O_NONBLOCK)
        except:
            log.exception('unable to open pipe')
            return None
        else:
            log.debug('opened pipe "{}" ({})'.format(self.pipe_path, pipe))
        return pipe

    def start(self):
        """Start the daemon"""
        # Run while exit event is not set

        pipe = self._make_pipe()
        try:
            log.debug('starting dataplicity service')

            while not self.exit_event.is_set():
                try:
                    self.poll()
                except:
                    log.exception('error in poll')

                start = time.time()
                while time.time() - start < self.poll_rate_seconds and not self.exit_event.is_set():
                    if pipe is not None:
                        command = os.read(pipe, 128)
                        if command:
                            command = command.splitlines()[-1].rstrip('\n')
                            self.on_client_command(command)
        finally:
            if pipe:
                try:
                    os.close(pipe)
                except:
                    pass
        log.debug('daemon is exiting')

        if self.exit_event.is_set() and self.exit_command is not None:
            time.sleep(1)  # Maybe redundant
            log.debug("Executing %s" % self.exit_command)
            os.system(self.exit_command)

    def exit(self, exit_command=None):
        self.exit_event.set()

    def poll(self):
        pass

    def on_client_command(self, command):
        if command == 'RESTART':
            log.info('restart requested')
            self.exit(' '.join(sys.argv))
        elif command == 'STOP':
            log.info('stop requested')
            self.exit()
        elif command == 'STATUS':
            log.info('status requested')
            return True
        return False

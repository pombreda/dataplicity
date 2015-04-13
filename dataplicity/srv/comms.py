"""

Dataplicity SRV comms


"""

from __future__ import unicode_literals
from __future__ import print_function

import os


from dataplicity.srv import constants


class CommsError(Exception):
    pass


class Comms(object):

    def __init__(self, pipe_path=constants.DATAPLICITY_SRV_PIPE):
        self.pipe_path = pipe_path

    def __call__(self, command):
        try:
            pipe = os.open(self.pipe_path, os.O_WRONLY | os.O_NONBLOCK)
        except:
            raise CommsError("Unable to connect to server via named pipe '{}'".format(self.pipe_path))
        try:
            os.write(pipe, command + '\n')
        finally:
            os.close(pipe)

    def sync(self):
        return self('SYNC')

    def restart(self):
        return self('RESTART')

    def stop(self):
        return self('STOP')

    def status(self):
        try:
            self('STATUS')
        except:
            return False
        else:
            return True

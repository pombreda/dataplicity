import getpass
from dataplicity.app.subcommand import SubCommand
from dataplicity.app.subcommands.build import do_build
from dataplicity import firmware
from dataplicity.client import tools
from dataplicity.app.errorcodes import ErrorCodes
from dataplicity.jsonrpc import JSONRPCError

from fs.opener import fsopendir
from fs.path import dirname, join
from fs.errors import ResourceNotFoundError

from base64 import b64encode
import logging
log = logging.getLogger('dataplicity')


class Publish(SubCommand):
    """Publish a firmware zip"""
    help = "Publish firmware"

    def add_arguments(self, parser):
        parser.add_argument('-r', '--replace', dest="replace", action="store_true", default=False,
                            help="Replace existing firmware if it exists")
        parser.add_argument('-i', '--increment', dest="bump", action="store_true", default=False,
                            help="Increment the version number after publishing")
        parser.add_argument('-b', '--build', dest="build", action="store_true", default=False,
                            help="Build the current firmware")

    def run(self):
        username = raw_input('username: ')
        password = getpass.getpass('password: ')

        log.setLevel(logging.ERROR)
        args = self.args

        conf_path = self.app.conf

        dataplicity_path = dirname(conf_path)

        if args.build:
            do_build(dataplicity_path)

        with fsopendir(dataplicity_path) as src_fs:
            version = firmware.get_version(src_fs)

            filename = "firmware-{}.zip".format(version)
            firmware_path = join('__firmware__', filename)
            try:
                firmware_contents = src_fs.getcontents(firmware_path, 'rb')
            except ResourceNotFoundError:
                print "{} is missing, you can build firmware with 'dataplicity build'".format(firmware_path)
                return -1

        firmware_b64 = b64encode(firmware_contents)

        client = self.app.make_client(log)
        conf = client.conf
        remote = client.remote

        device_class_name = conf.get('device', 'class')
        #serial = conf.get('device', 'serial')

        ui = firmware.get_ui(fsopendir(dataplicity_path))

        print "uploading firmware..."
        with remote.batch() as batch:
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=device_class_name,
                               serial=client.serial,
                               auth_token=client.auth_token)
            batch.call_with_id("publish_result",
                               "device.publish",
                               device_class=device_class_name,
                               version=version,
                               firmware_b64=firmware_b64,
                               ui=ui,
                               username=username,
                               password=password,
                               replace=args.replace)

        batch.get_result('auth_result')
        try:
            publish_result = batch.get_result('publish_result')
        except JSONRPCError as e:
            if e.code == ErrorCodes.FIRMWARE_EXISTS:
                print "Firmware {:010} exists!\nBump the version number in firmware.conf or use --replace to overwrite".format(version)
                return -1
            raise

        print "visit {} to manage firmware".format(publish_result['url'])

        if args.bump:
            with fsopendir(dataplicity_path) as src_fs:
                firmware.bump(src_fs)

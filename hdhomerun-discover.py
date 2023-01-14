#! /usr/bin/python3
# -*- coding: utf-8 -*-

""" See if the HDHomeRun box is accessible and running

Can be called with a optional IP address(s) for users that
have multiple HDHRs that have STATIC addresses.

Expects a writable log file in /tmp named hdhr_discovery.log.
Owner:group = mythtv:mythtv and mode = 664.

Exit codes are:

    5 times the number of failing HDHRs
    4 if the user running the program isn't what systemd is using
    3 if the logfile isn't writable
    2 for a keyboard interrupt
    1 no discovery output or IPv4 and IPv6 address found
    0 if all HDHR(s) are found (success case)
"""

__version__ = '1.14'

import argparse
import getpass
import subprocess
import sys
import logging
from time import sleep
from datetime import datetime

ATTEMPTS = 21
DELAY = 2


# pylint: disable=consider-using-f-string,consider-using-with
def get_program_arguments():
    ''' Process the command line. '''

    parser = argparse.ArgumentParser(description='HDHR Access Test',
                                     epilog='*  Default values are in ()s.')

    parser.add_argument('IP_ADDRESSES', type=str, metavar='<IP>', default=None,
                        nargs='*', help='Optional IP address(s) (%(default)s)')

    parser.add_argument('--logfile', default='/tmp/hdhr_discovery.log',
                        type=str, metavar='<lf>',
                        help='Location of log file (%(default)s)')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    return vars(parser.parse_args())


def get_elapsed_time(start):
    ''' Calculate the time spent waiting for the HDHR to come up '''

    delta = datetime.utcnow() - start
    rounded_delta = '{:.3f}'.format(delta.seconds +
                                    (delta.microseconds / 1000000))
    return rounded_delta


def main(ip_address, logfile):
    ''' Try to discover the HDHR(s) '''

    attempt = 0  # Shut up pylint.
    command = ['systemctl', 'show', '--property=User', '--value',
               'mythtv-backend.service']

    systemd_user = subprocess.check_output(command, stderr=subprocess.STDOUT).\
                                           strip().decode()
    if not systemd_user:
        systemd_user = 'root'

    if getpass.getuser() != systemd_user:
        print('BE running as user %s, not your user, aborting!' % systemd_user)
        sys.exit(4)

    if ip_address is None:
        command = ['hdhomerun_config', 'discover']
    else:
        command = ['hdhomerun_config', 'discover', ip_address]

    logger = logging.getLogger(command[0])

    try:
        logging.basicConfig(filename=logfile, filemode='a',
                            format='%(asctime)s %(levelname)s\t%(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
    except PermissionError:
        print('%s is not writable, aborting!' % logfile)
        sys.exit(3)

    logger.info('Starting HDHomeRun discovery')

    start = datetime.utcnow()

    for attempt in range(1, ATTEMPTS):
        try:
            discovery_response = subprocess.check_output(command,
                                    stderr=subprocess.STDOUT).decode().split()
        except KeyboardInterrupt:
            sys.exit(2)
        except subprocess.CalledProcessError:
            logger.warning('%s failed, keep looking.', command[0])
            sleep(DELAY)
            continue

        if not discovery_response:
            logger.error('No output from %s, aborting!', command)
            sys.exit(1)

        if len(discovery_response) > 6:
            logger.error('%s got multiple IPs. Disable IPv6, aborting!',
                         command)
            sys.exit(1)

        if discovery_response[0] != 'hdhomerun':
            logger.warning('%s got an unexpected response.', command)
            sleep(DELAY)
        else:
            logger.info('Found HDHomeRun%s. Seconds=%s, attempts=%d.',
                        '' if ip_address is None else (' for ' + ip_address),
                        get_elapsed_time(start), attempt)
            return 0

    logger.error('Could not find any HDHomeRun%s. Seconds=%s, attempts=%d.',
                 '' if ip_address is None else (' for ' + ip_address),
                 get_elapsed_time(start), attempt)

    return 5


if __name__ == '__main__':

    ARGS = get_program_arguments()

    if not ARGS['IP_ADDRESSES']:
        RETURN_VALUE = main(None, ARGS['logfile'])
    else:
        RETURN_VALUE = 0
        for address in ARGS['IP_ADDRESSES']:
            RETURN_VALUE += main(address, ARGS['logfile'])

    sys.exit(RETURN_VALUE)

# vim: set expandtab tabstop=4 shiftwidth=4 smartindent colorcolumn=80:

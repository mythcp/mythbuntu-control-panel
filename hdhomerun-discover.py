#! /usr/bin/python3
# -*- coding: utf-8 -*-

""" See if the HDHomerun box(s) are accessible and running

Requires Python 3.6 or later. Typically, this file is put in
/usr/local/bin then chmod to 755.

For backends started by systemd, use:

    sudo --preserve-env systemctl edit --force mythtv-backend.service

and modify or add in the [Service] section:

ExecStartPre=-/usr/local/bin/hdhomerun-discover.py

Can be called with optional hostname(s)/IP address(s) for users that
have multiple HDHRs. IP addresses sould need to be STATIC.

Use --help to see all options.

If run from the command line, then output will be to the screen.
Otherwise, a log file in /tmp named hdhr_discovery.log is made.
Changable with the --logfile switch.

Exit codes:

    0 = success (for *ALL* HDHRs if multiple IPs were specified)
    1 = no output from the hdhomerun_config discover command or not found
    3 = logfile is not writable, delete it and try again
    4 = keyboard interrupt
    5+ = one or more (of multiple hosts) failed

"""

__version__ = '1.35'

import argparse
import signal
import socket
import subprocess
import sys
import datetime
from os.path import basename
from os import _exit
from time import sleep


# pylint: disable=too-many-arguments,unused-argument
def keyboard_interrupt_handler(sigint, frame):
    ''' Handle all KeyboardInterrupts here. And, just leave. '''
    _exit(4)
# pylint: enable=unused-argument


def get_program_arguments():
    ''' Process the command line. '''

    parser = argparse.ArgumentParser(description='HDHR Access Test',
                                     epilog='*  Default values are in ()s')

    parser.add_argument('HDHRS', type=str,  default=None, nargs='*',
                        help='optional hostnames/IPs (%(default)s)')

    parser.add_argument('--attempts', default=20, type=int, metavar='<num>',
                        help='number of tries to find HDHRs (%(default)i)')

    parser.add_argument('--debug', action='store_true',
                        help='output additional information (%(default)s)')

    parser.add_argument('--logfile', default='/tmp/hdhr_discovery.log',
                        type=str, metavar='<lf>',
                        help='optional path + name of log file (%(default)s)')

    parser.add_argument('--sleep', default=1.5, type=float, metavar='<sec>',
                        help='seconds betweem attempts (%(default)s)')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    return parser.parse_args()


def get_elapsed_time(start):
    ''' Calculate the time spent waiting for the HDHR to come up. '''

    delta = datetime.datetime.now(datetime.timezone.utc) - start

    return f'{delta.seconds + (delta.microseconds / 1000000):.3f}'


def log_or_print(loglevel, message, output):
    ''' Add timestamp, log level then print to the selected location. '''

    print(datetime.datetime.now().strftime("%F %T.%f")[:-3],
          f'{loglevel:8}', message, file=output)


def last_message(loglevel, result, host, start, attempt, output):
    ''' Common success or failure message text. '''

    log_or_print(loglevel, f'{result} {"at " + host + " " if host else ""}'
                 f'in {get_elapsed_time(start)} seconds '
                 f'and {attempt} attempt{"s"[attempt == 1:]}\n', output)


def check_one_device(host, args, output):
    ''' Try to discover the HDHR(s). '''

    attempt = 0
    command = ['hdhomerun_config', 'discover']
    start = datetime.datetime.now(datetime.timezone.utc)

    if host:
        command.append(host)

    for attempt in range(1, args.attempts+1):

        try:
            discovery_response = subprocess.check_output(
                command, text=True, stderr=subprocess.STDOUT).split()
        except FileNotFoundError:
            log_or_print('ERROR', f'{command[0]}: command not found', output)
            sys.exit(1)
        except subprocess.CalledProcessError:
            log_or_print('WARNING', f'{command[0]}: got no response '
                         f'from {host}, attempt: {attempt:2}', output)
            sleep(args.sleep)
            continue

        if not discovery_response:
            log_or_print('ERROR', f'No output from {command[0]}, aborting!',
                         output)
            sys.exit(1)

        if args.debug:
            log_or_print('DEBUG', f'Got: {" ".join(discovery_response)}',
                         output)

        if discovery_response.count('hdhomerun') > 1:
            log_or_print('INFO', f'{command[0]}: got more than 1 IP.', output)
            continue

        if discovery_response[0] != 'hdhomerun':
            # TODO: consider making this an ERROR and exiting not sleeping...
            log_or_print('WARNING', f'{command[0]} got an unexpected response:'
                         f' {" ".join(discovery_response)}',
                         output)
            sleep(args.sleep)
        else:
            last_message('INFO', f'Found HDHR {discovery_response[2]}', host,
                         start, attempt, output)
            return 0

    last_message('ERROR', 'No HDHR found', host, start, attempt, output)

    return 5


def main(args, output=None):
    ''' Control checking of one or more devices. '''

    log_or_print('INFO', f'Starting {basename(__file__)} v{__version__}, '
                 f'attempts={args.attempts}, sleep={args.sleep:.2f}', output)

    if args.HDHRS:

        return_value = 0

        for hdhr in args.HDHRS:

            try:
                ip_address = socket.gethostbyname(hdhr)
            except socket.gaierror:
                log_or_print("ERROR", f"Couldn't resolve {hdhr}", output)
                continue

            return_value += check_one_device(ip_address, args, output)

    else:
        return_value = check_one_device(None, args, output)

    return return_value


if __name__ == '__main__':

    RETURN_VALUE = 0
    signal.signal(signal.SIGINT, keyboard_interrupt_handler)

    ARGS = get_program_arguments()

    if sys.stdin and sys.stdin.isatty():
        RETURN_VALUE = main(ARGS)
    else:
        try:
            with open(ARGS.logfile, encoding='ascii', mode='a') as file_object:
                RETURN_VALUE += main(ARGS, output=file_object)
        except PermissionError:
            print(f'Can\'t write to {ARGS.logfile}, aborting!')
            sys.exit(3)

    sys.exit(RETURN_VALUE)

# vim: set expandtab tabstop=4 shiftwidth=4 smartindent colorcolumn=80:

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##############################################################################
# Wait until a given IP address or DNS name is pingable, or a timeout occurs.
#
# Intended to be used in the ExecStartPre line of a systemd unit.
#
# Logs to syslog.
#
# Author:        J S Worthington
# Creation date: 18-Dec-2018
##############################################################################

VERSION='0.1 18-Dec-2018'
PROGRAM_NAME='wait-until-pingable'

import argparse
import syslog
import os, sys, socket, struct, select, time, signal


##############################################################################
# Configuration

# True to use debugging code, False otherwise.
# Set debug=True here if debugging code is needed before parser.parse_args()
# has been run.  Otherwise, use the --debug command line option.
debug = False

# Ping size.  Number of bytes of data to send in the ping.
ping_size = 1


##############################################################################
# Debug functions

def debug_print_real(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

def debug_print_pass(*args, **kwargs):
    pass

def setup_debug():
    global debug_print
    if debug:
        debug_print = debug_print_real
        debug_print('Debugging enabled')
    else:
        debug_print = debug_print_pass

setup_debug()


##############################################################################
# Python 3 ping from:
#   http://pastebin.com/4ZHR61BH
# Cut down and altered by JSW 9-Dec-2012

"""
    A pure python ping implementation using raw sockets.

    Note that ICMP messages can only be sent from processes running as root
    (in Windows, you must run this script as 'Administrator').

    Original Version from Matthew Dixon Cowles:
      -> ftp://ftp.visi.com/users/mdc/ping.py

    Rewrite by Jens Diemer:
      -> http://www.python-forum.de/post-69122.html#69122

    Rewrite by George Notaras:
      -> http://www.g-loaded.eu/2009/10/30/python-ping/

    Enhancements by Martin Falatic:
      -> http://www.falatic.com/index.php/39/pinging-with-python

    Edited by yokmp:
	I've done this because some lines doesn't work in Python3.2 and i needed it
	a bit more interactive. See the last lines for detail.

    ===========================================================================
"""

# ICMP parameters

ICMP_ECHOREPLY = 0 # Echo reply (per RFC792)
ICMP_ECHO = 8 # Echo request (per RFC792)
ICMP_MAX_RECV = 2048 # Max size of incoming buffer

MAX_SLEEP = 1000

ERROR_DNS_LOOKUP_FAILED = -2
ERROR_SENDTO_FAILED = -3

def checksum(source_string):
    """
    A port of the functionality of in_cksum() from ping.c
    Ideally this would act on the string as a series of 16-bit ints (host
    packed), but this works.
    Network data is big-endian, hosts are typically little-endian
    """
    countTo = (int(len(source_string) / 2)) * 2
    sum = 0
    count = 0

    # Handle bytes in pairs (decoding as short ints)
    loByte = 0
    hiByte = 0
    while count < countTo:
        if (sys.byteorder == "little"):
            loByte = source_string[count]
            hiByte = source_string[count + 1]
        else:
            loByte = source_string[count + 1]
            hiByte = source_string[count]
        sum = sum + (hiByte * 256 + loByte)
        count += 2

    # Handle last byte if applicable (odd-number of bytes)
    # Endianness should be irrelevant in this case
    if countTo < len(source_string): # Check for odd length
        loByte = source_string[len(source_string) - 1]
        sum += loByte

    sum &= 0xffffffff # Truncate sum to 32 bits (a variance from ping.c, which
                      # uses signed ints, but overflow is unlikely in ping)

    sum = (sum >> 16) + (sum & 0xffff)    # Add high 16 bits to low 16 bits
    sum += (sum >> 16)                    # Add carry from above (if any)
    answer = ~sum & 0xffff                # Invert and truncate to 16 bits
    answer = socket.htons(answer)

    return answer


def send_one_ping(mySocket, destIP, myID, mySeqNumber, numDataBytes):
    """
    Send one ping to the given >destIP<.
    """
    debug_print('send_one_ping')
    try:
        destIP = socket.gethostbyname(destIP)
        debug_print('destIP=' + destIP)
    except socket.gaierror as e:
        return ERROR_DNS_LOOKUP_FAILED


    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0

    # Make a dummy heder with a 0 checksum.
    header = struct.pack(
        "!BBHHH", ICMP_ECHO, 0, myChecksum, myID, mySeqNumber
    )

    padBytes = []
    startVal = 0x42
    for i in range(startVal, startVal + (numDataBytes)):
        padBytes += [(i & 0xff)]  # Keep chars in the 0-255 range
    data = bytes(padBytes)

    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data) # Checksum is in network order

    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.
    header = struct.pack(
        "!BBHHH", ICMP_ECHO, 0, myChecksum, myID, mySeqNumber
    )

    packet = header + data

    sendTime = time.time()

    try:
        mySocket.sendto(packet, (destIP, 1)) # Port number is irrelevant for ICMP
    except socket.error as e:
        debug_print("General failure (%s)" % (e.args[1]))
        return ERROR_SENDTO_FAILED

    return sendTime


def receive_one_ping(mySocket, myID, timeout):
    """
    Receive the ping from the socket. Timeout = in ms
    """
    timeLeft = timeout / 1000

    while True: # Loop while waiting for packet or timeout
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return None, 0, 0, 0, 0

        timeReceived = time.time()

        recPacket, addr = mySocket.recvfrom(ICMP_MAX_RECV)

        ipHeader = recPacket[:20]
        iphVersion, iphTypeOfSvc, iphLength, \
        iphID, iphFlags, iphTTL, iphProtocol, \
        iphChecksum, iphSrcIP, iphDestIP = struct.unpack(
            "!BBHHHBBHII", ipHeader
        )

        icmpHeader = recPacket[20:28]
        icmpType, icmpCode, icmpChecksum, \
        icmpPacketID, icmpSeqNumber = struct.unpack(
            "!BBHHH", icmpHeader
        )

        if icmpPacketID == myID: # Our packet
            dataSize = len(recPacket) - 28
            return timeReceived, dataSize, iphSrcIP, icmpSeqNumber, iphTTL

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return None, 0, 0, 0, 0


def one_ping(destIP, timeout, mySeqNumber, numDataBytes):
    """
    Returns either the delay (in ms) or None on timeout.
    """

    delay = None

    try: # One could use UDP here, but it's obscure
        mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp"))
    except (socket.error, (errno, msg)):
        if errno == 1:
            # Operation not permitted - Add more information to traceback
            etype, evalue, etb = sys.exc_info()
            evalue = etype(
                "%s - Note that ICMP messages can only be sent from processes running as root." % evalue
            )
            raise (etype, evalue, etb)

        debug_print("failed. (socket error: '%s')" % msg)
        raise # raise the original error

    my_ID = os.getpid() & 0xFFFF

    sentTime = send_one_ping(mySocket, destIP, my_ID, mySeqNumber, numDataBytes)
    if sentTime == None:
        mySocket.close()
        return delay
    elif sentTime < 0:
        mySocket.close()
        return sentTime

    recvTime, dataSize, iphSrcIP, icmpSeqNumber, iphTTL = receive_one_ping(mySocket, my_ID, timeout)

    mySocket.close()

    if recvTime:
        delay = (recvTime - sentTime) * 1000
        debug_print("%d bytes from %s: icmp_seq=%d ttl=%d time=%d ms" % (
            dataSize, socket.inet_ntoa(struct.pack("!I", iphSrcIP)), icmpSeqNumber, iphTTL, delay)
        )
    else:
        delay = None
        debug_print("Request timed out.")

    if debug:
        global kill_ping
        if kill_ping != 0:
            kill_ping -= 1
            debug_print("Ping killed")
            delay = None

    return delay


##############################################################################
# Signal handler

def handle_signal(signum, stack):
    global stop
    if signum in [1,2,3,15]:
        debug_print('Caught signal ', str(signum), ', stopping.', sep='')
        stop = True
    elif debug and signum == 20:
        global kill_ping
        kill_ping += 1
    else:
        debug_print('Caught signal ', str(signum), ', ignoring.', sep='')


##############################################################################
# Ping

def ping():
    global args, ping_size
    ping.ping_id += 1
    if ping.ping_id >= 100:
        ping.ping_id = 1
    return one_ping(args.ping_target, args.ping_timeout, ping.ping_id, ping_size)
ping.ping_id = 0


##############################################################################
# Main

parser = argparse.ArgumentParser(
    description='Wait until a ping response is received or timeout',
    formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=15)
    )
parser.add_argument('ping_target', default='google.com', nargs='?', help='name or IP address to ping (default=google.com).  Note: IPv6 not supported yet.')
parser.add_argument('timeout', default=30, type=int, nargs='?', help='maximum time to keep trying to get a ping response (seconds, int, default=30)')
parser.add_argument('-d', '--ping_delay', default=1.0, type=float, help='delay between pings (seconds, float, default=1.0)')
parser.add_argument('-p', '--ping_timeout', default=1000, type=int, help='time to wait for a ping response (miliseconds, int, default=1000)')
parser.add_argument('-v', '-V', '--version', dest='display_version', default=False, action='store_true')
parser.add_argument('--debug', default=False, action='store_true',
                    help='Enable debugging and debug output to the console.  Do not use this option when using ' + PROGRAM_NAME + ' in a systemd unit.')

args = parser.parse_args()
if args.debug:
    debug = True
    setup_debug()

if args.display_version:
    print(PROGRAM_NAME + ' version ' + VERSION)
    exit(0)

stop = False
end_time = time.time() + args.timeout

if debug:
    kill_ping = 0

# Set up signal handler.  Catch all catchable signals and have them stop the
# program.
uncatchable = ['SIG_DFL', 'SIGSTOP', 'SIGKILL', 'SIG_BLOCK']
for i in [x for x in dir(signal) if x.startswith("SIG")]:
    if not i in uncatchable:
        signum = getattr(signal, i)
        signal.signal(signum, handle_signal)

syslog.syslog("Starting")

while not stop:

    response = ping()
    if response != None and response > 0:
        break
    time.sleep(args.ping_delay)
    if time.time() >= end_time:
        stop = True

if stop:
    if response != None and response < 0:
        if response == ERROR_DNS_LOOKUP_FAILED:
            syslog.syslog('DNS lookup failed')
        elif response == ERROR_SENDTO_FAILED:
            syslog.syslog('sendto failed!')
        exit_val = -response
    else:
        exit_val = 1
else:
    exit_val = 0
    syslog.syslog('ping of ' + str(args.ping_target) + ' succeeded')
debug_print('exit_val=' + str(exit_val))
syslog.syslog("Exiting")
exit(exit_val)

#! /usr/bin/python3

import subprocess, datetime, time, sys, os

current_date_time = datetime.datetime.now()
log_msg = current_date_time.strftime("%Y-%m-%d %H:%M:%S") + " Attempting to discover HDHomeRun device\n"
found = False
for attempt in range(10):
    if subprocess.run(['hdhomerun_config', 'discover']).returncode == 0:
        current_date_time = datetime.datetime.now()
        log_msg = log_msg + current_date_time.strftime("%Y-%m-%d %H:%M:%S") + " HDHomeRun device successfully found"
        found = True
        break
    if attempt == 9:
        log_msg = log_msg + " HDHomeRun device was not found after 10 attempts"
        break
    time.sleep(3)

if os.path.exists('/tmp/hdhomerun-discover.out'):
    sys.exit(0)
else:
    with open('/tmp/hdhomerun-discover.out', 'w') as txt_file:
        txt_file.write(log_msg)
    if not found:
        sys.exit(1)

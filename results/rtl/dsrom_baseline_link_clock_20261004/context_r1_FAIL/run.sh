#!/bin/bash
cd /home/ubuntu/maxwell-dsrom-baseline-link-clock-1664/src
python3 tools/dsrom_baseline_link_clock.py route --work /home/ubuntu/maxwell-dsrom-baseline-link-clock-1664/context-r1
rc=$?
printf "%s\n" "$rc" > /home/ubuntu/maxwell-dsrom-baseline-link-clock-1664/context-r1/exit.code
exit "$rc"

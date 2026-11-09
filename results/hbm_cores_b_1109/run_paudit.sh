#!/bin/bash
for h in epyc4 epyc5 epyc6 epyc2; do
( timeout 3000 ssh -n -o ControlPath=none $h 'cd / && nice -n19 ionice -c3 python3 -I ~/disk-urgent-3/paudit.py 2>&1 | tail -3 | cut -c1-900' ) &
done
wait
echo PAUDIT-DONE

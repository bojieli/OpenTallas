#!/bin/bash
for h in epyc2 epyc5; do
 ( timeout 1500 ssh -n -o ControlPath=none $h "cd / && before=\$(df -BG --output=avail /srv/opentallas-scratch2 / | tail -2 | tr -d ' ' | tr '\n' ' '); python3 -I ~/disk-urgent-3/d3_del.py ~/disk-urgent-3/s2.eval.tsv ~/disk-urgent-3/$h.final apply 2>&1 | cut -c1-200; echo \$(hostname) before \$before after \$(df -BG --output=avail /srv/opentallas-scratch2 / | tail -2 | tr -d ' ' | tr '\n' ' ')" ) &
done
wait

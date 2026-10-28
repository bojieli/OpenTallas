#!/bin/bash
set -e
cd /srv/opentallas-scratch2/claude/die-qc10-1028
bash kit8.sh > kit8.log 2>&1; echo "kit rc $? $(date)" >> chain8.status
bash bays8.sh > bays8.log 2>&1; echo "bays rc $? $(date)" >> chain8.status
python3 overlay8.py > overlay8.log 2>&1; echo "overlay rc $? $(date)" >> chain8.status
bash run_clock8.sh TT > grt8_TT.log 2>&1 & bash run_clock8.sh FF > grt8_FF.log 2>&1 & wait; echo "grt done $(date)" >> chain8.status

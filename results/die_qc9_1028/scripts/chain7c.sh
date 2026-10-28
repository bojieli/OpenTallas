#!/bin/bash
set -e
cd /srv/opentallas-scratch2/claude/die-qc9-1028
bash kit7c.sh > kit7c.log 2>&1
bash bays7c.sh > bays7c.log 2>&1
python3 overlay7c.py > overlay7c.log 2>&1

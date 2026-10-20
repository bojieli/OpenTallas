#!/bin/bash
set -euo pipefail
cd /work/src
mkdir -p /work/generic7
yosys -Q -s full_generic7.ys > /work/generic7/generic.log 2>&1
echo GENERIC_DONE; grep -iE 'warning.*(undriven|latch)|ERROR' /work/generic7/generic.log | head -5 || true
python3 construct_parent7.py 2>&1 | tail -5
bash native7.sh

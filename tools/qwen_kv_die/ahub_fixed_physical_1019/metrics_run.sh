#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /run
openroad -exit final_native.tcl > final_native.log 2>&1
python3 metrics.py > metrics.log 2>&1

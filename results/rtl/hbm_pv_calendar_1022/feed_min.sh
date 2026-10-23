#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/hbm-pv-calendar-1022
python3 feed_min.py
cd feed_min
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb -j 2 -Wno-fatal --Mdir obj selected_feed.sv tb.sv > build.log 2>&1
obj/Vtb > run.log 2>&1
cat run.log

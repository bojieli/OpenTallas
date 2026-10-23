#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/hbm-pv-calendar-1022
P=/srv/opentallas-scratch/claude/hbmc-token2/pv_r18_probe/masters
ulimit -s unlimited
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -Wno-fatal --top-module tb -j 4 --Mdir pt_obj "$P/ot_hbm_su_static_pgslice_lg.sv.orig" "$P/ot_hbm_su_static_qcore_r13.sv" pt_latency.sv > pt_build.log 2>&1
pt_obj/Vtb > pt_latency.log 2>&1
cat pt_latency.log

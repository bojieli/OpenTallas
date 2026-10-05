#!/bin/bash
set -eu
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -Wno-fatal -j 16 --top-module tb_pcwb_command_match_lockstep \
  --Mdir lockstep_obj ot_hbm_accel_stream_pc_wb_digest.sv \
  ot_hbm_accel_stream_pc_wb_command_match.sv tb_pcwb_command_match_lockstep.sv >lockstep_build.log 2>&1
./lockstep_obj/Vtb_pcwb_command_match_lockstep +seed=26 +cycles=100000 >lockstep.log 2>&1
python3 run_connected.py

#!/bin/bash
set -euo pipefail
w2_run=/srv/opentallas-scratch2/scratch/codex/w2-phase-seat-19a1b52dc
cd "$w2_run/src"
python3 physical/hbm_w2_rb_station_20261006/prepare.py
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
export OT_ORFS_CORNER_OVERRIDE=TC
export OT_ROUTE_HOLD_CORNERS=mm
export CL_PHASE=calibrate
python3 physical/hbm_w2_rb_station_20261006/run_owned.py --run "$w2_run/physical_no2_cal" --no 2 --safe --phase-seat --core-width 480 --core-height 200 --place-density 0.40 --period-ps 730 --hold-margin-ns 0.010 --threads 16 --tag codex_W2_phase_seat --pnr-stop-after cts
python3 tools/closure_loop/ck_insertion.py --help > "$w2_run/ck_insertion.help"
printf 'CALIBRATION_READY\n' > "$w2_run/physical.stage"

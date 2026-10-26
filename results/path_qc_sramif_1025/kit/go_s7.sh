#!/bin/bash
# PATH-QC-SRAMIF s7 (ot-run job): synth (RTL MIF=1 via VERILOG_TOP_PARAMS) -> floorplan -> place with the F6 anchors
# (pre_gpl_s7.tcl) -> keep-check of the per-SRAM copies in the Yosys netlist -> stageA.sh (6-trunk mscts CTS + GRT +
# per-corner bound + FF-only GRT hold repair, OT_S6_HOLD_MARGIN=0 per GEOM-REVIEW 08:58) -> F6 dump.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
echo "go_s7 start $(date -Is) host $(hostname)" >> "$K/image.txt"
"$K/run_kit.sh" "$K" place 32 16; rc=$?
echo "go_s7 place rc $rc $(date -Is)" >> "$K/image.txt"
[ $rc = 0 ] || exit $rc
python3 -I "$K/keep_check.py" "$K" > "$K/keep_check.txt" 2>&1; rc=$?; cat "$K/keep_check.txt"
[ $rc = 0 ] || { echo "go_s7 KEEP_CHECK FAIL" >> "$K/image.txt"; exit 7; }
OT_S6_HOLD_MARGIN=0 "$K/stageA.sh" "$K"; rc=$?
echo "go_s7 stageA rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 3_place > "$K/f6_place.log" 2>&1
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
exit $rc

#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
files=$(cat source.f | grep -v -E 'lpf_hp|headprep/h16z')
for mode in positive mutant; do
 part=gi_actual_cut.sv
 [ "$mode" = mutant ] && part=gi_wrong_late_pos.sv
 "$V" --binary -j 4 --timing -Wno-fatal -Wno-lint -Wno-style -O1 --top-module tb $files gi_original_cut.sv "$part" tb_gi.sv -Mdir "obj_gi_$mode" > "gi_${mode}_build.log" 2>&1
 set +e
 "obj_gi_$mode/Vtb" > "gi_$mode.log" 2>&1
 rc=$?
 set -e
 if [ "$mode" = positive ]; then [ "$rc" = 0 ];grep -q GI_OUTPUT_CUT_PASS "gi_$mode.log";else [ "$rc" != 0 ];grep -q 'actual pre-edge bank export mismatch' "gi_$mode.log";fi
 tail -n 3 "gi_$mode.log"
done
echo GI_OUTPUT_CUT_CAUSAL_UNIT_PASS

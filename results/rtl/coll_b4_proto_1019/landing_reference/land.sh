#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/coll-b4-land-proto-1019
cd "$D/src"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$D/out"
for mode in golden rsel naive encomb; do
 def=()
 case $mode in rsel) def=(+define+OT_QFD_LAND_MUT_RSEL);; naive) def=(+define+OT_QFD_LAND_MUT_NAIVE);; encomb) def=(+define+OT_QFD_LAND_MUT_ENCOMB);; esac
 verilator --binary --timing --top-module tb_land_b4 -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY "${def[@]}" --Mdir "$D/out/obj_$mode" rtl/test/qwen_coll_b4/tb_land_b4.sv rtl/rom/ot_coll_b4_land_reference.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv >"$D/out/build_$mode.log" 2>&1
 rc=0
 "$D/out/obj_$mode/Vtb_land_b4" >"$D/out/$mode.log" 2>&1 || rc=$?
 if [ "$mode" = golden ]; then cat "$D/out/$mode.log"; test "$rc" = 0; grep -q 'B4_LAND PASS' "$D/out/$mode.log"; else test "$rc" != 0; grep -q 'B4_LAND_MISMATCH' "$D/out/$mode.log"; echo "B4_LAND MUTANT_CAUGHT $mode rc=$rc"; fi
done

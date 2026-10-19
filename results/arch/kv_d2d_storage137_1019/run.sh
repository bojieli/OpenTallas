#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
command -v iverilog
iverilog -V >out/iverilog_version.log 2>&1
common=(tb.sv original_leaf.sv original_macro512.v)
for mode in good no_h0 no_h1 swap_group new_macro; do
 cp replay_sf137_private.sv out/candidate.sv
 cp ot_sram_1r1w_64x137_m1_r2c2_p192.v out/macro.v
 python3 mutate.py "$mode"
 iverilog -g2012 -DOT_MEM_NO_INIT -s tb -o "out/$mode.vvp" "${common[@]}" out/candidate.sv out/macro.v
 set +e
 vvp "out/$mode.vvp" >"out/$mode.log" 2>&1
 rc=$?
 set -e
 if [[ "$mode" == good ]]; then
   [[ "$rc" == 0 ]] && grep -q '^PASS ' "out/$mode.log"
 else
   [[ "$rc" != 0 ]] && grep -Eq 'LEAF_SCOREBOARD|MACRO_OLD_COLLISION' "out/$mode.log"
 fi
 printf '%s rc=%s\n' "$mode" "$rc" | tee -a out/verdicts.log
done

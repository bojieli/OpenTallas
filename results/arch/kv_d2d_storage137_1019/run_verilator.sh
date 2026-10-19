#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version | tee out/verilator_version.log
grep -q 'Verilator 5.050' out/verilator_version.log
for mode in good no_h0 no_h1 swap_group new_macro; do
 cp replay_sf137_private.sv out/candidate.sv
 cp ot_sram_1r1w_64x137_m1_r2c2_p192.v out/macro.v
 python3 mutate.py "$mode"
 verilator --binary --timing -Wno-fatal -j 4 +define+OT_MEM_NO_INIT --top-module tb --Mdir "out/vlt_$mode" tb.sv original_leaf.sv original_macro512.v out/candidate.sv out/macro.v >"out/verilator_build_$mode.log" 2>&1
 set +e
 "out/vlt_$mode/Vtb" >"out/verilator_$mode.log" 2>&1
 rc=$?
 set -e
 if [[ "$mode" == good ]]; then
   [[ "$rc" == 0 ]] && grep -q '^PASS ' "out/verilator_$mode.log"
 else
   [[ "$rc" != 0 ]] && grep -Eq 'LEAF_REFERENCE|MACRO_OLD_COLLISION' "out/verilator_$mode.log"
 fi
 printf '%s rc=%s\n' "$mode" "$rc" | tee -a out/verilator_verdicts.log
done

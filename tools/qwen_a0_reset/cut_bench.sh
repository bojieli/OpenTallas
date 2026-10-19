#!/bin/bash
set -euo pipefail
python3 cut_bench.py
mkdir -p cut
V="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$V" --binary --timing -j 4 -O2 -Wno-fatal --top-module tb_a0_reset_cut -Mdir cut/obj native/native_cells.v native/reset_cut.v native/tb_cut.sv > cut/build.log 2>&1
sha256sum native/native_cells.v native/reset_cut.v native/tb_cut.sv cut/obj/Vtb_a0_reset_cut > cut/source.sha256
cut/obj/Vtb_a0_reset_cut +MUT=0 | tee cut/run_0.log
grep -q '^A0_RESET_CUT_PASS ' cut/run_0.log
for mut in 41 42 43 44;do
 set +e;cut/obj/Vtb_a0_reset_cut +MUT="$mut" > "cut/run_$mut.log" 2>&1;rc=$?;set -e
 [[ "$rc" != 0 ]];grep -q 'A0_RESET_.*FAIL' "cut/run_$mut.log"
done
printf 'A0_RESET_CUT_ALL_PASS\n'

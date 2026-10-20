#!/bin/bash
set -eu
verilator=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$verilator --version
for c in positive sub5_mut; do
 mkdir -p "$c"
 defs=-DOT_BF_FOREP
 defs="$defs -DOT_BF_FOREP32 -DOT_BF_FINE32 -DOT_BF_SUB5"
 if [ "$c" = sub5_mut ]; then defs="$defs -DOT_BF_FOREP32_MUT_SUB"; fi
 $verilator --binary --timing --build -j 4 -Wno-fatal $defs --top-module tb --Mdir "$c/obj" tb.sv old_bterm.sv ot_v41_bterm4_w10.sv ot_v41_bterm.sv ot_prefix.sv ot_hdc_delay.sv > "$c/build.log" 2>&1
 set +e
 "$c/obj/Vtb" > "$c/run.log" 2>&1
 rc=$?
 set -e
 echo "$c rc=$rc"
 if [ "$c" = positive ];then test "$rc" -eq 0;grep 'BTERM_NATIVE32 PASS' "$c/run.log";else test "$rc" -ne 0;grep 'BTERM_DIFF' "$c/run.log";fi
done

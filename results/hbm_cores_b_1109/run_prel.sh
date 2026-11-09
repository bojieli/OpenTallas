#!/bin/bash
# Lockstep BM PREL=1 vs PREL=0; mutant OT_BM_PREL_MUT must be caught.
set -euo pipefail
cd "$(dirname "$0")"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
E=$PWD; D=$PWD/build; mkdir -p "$D"
RTL=$E/rtl
for mode in base mutant; do
 args=(); [ "$mode" = mutant ] && args+=(-DOT_BM_PREL_MUT)
 verilator --binary --timing --x-initial unique --x-assign unique -j 8 -O1 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir "$D/$mode" -o tb -I"$RTL" "${args[@]}" "$E/tb_prel.sv" "$RTL/ot_s81_kp4_bm.sv" "$RTL/ot_s81_kp4_common.sv" > "$E/$mode.build.log" 2>&1
 for seed in 11 12 13; do
  set +e; "$D/$mode/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$E/${mode}_s${seed}.log" 2>&1; rc=$?; set -e
  tail -3 "$E/${mode}_s${seed}.log"; echo "$mode seed $seed rc=$rc"
  if [ "$mode" = base ]; then test "$rc" = 0; else test "$rc" != 0; break; fi
 done
done
echo BM_PREL_RUN_PASS

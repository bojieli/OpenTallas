#!/bin/bash
set -euo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2;do
 "$VL" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_crom8_r3_abi_replay -GMUT=$m -GNMAX=164 --Mdir obj$m -f sources.f > build$m.log 2>&1
 for r in 0 1 2 3 4 5 6 7;do
  obj$m/Vtb_crom8_r3_abi_replay +OT_ROM_DIR="$PWD/r1/masks" +V="$PWD/replay_l0/rank$r/vec" +N=148 > run_m${m}_r${r}.log 2>&1
  if [ "$m" = 0 ];then grep -q '^PASS' run_m${m}_r${r}.log;else grep -q '^FAIL' run_m${m}_r${r}.log;fi
 done
done

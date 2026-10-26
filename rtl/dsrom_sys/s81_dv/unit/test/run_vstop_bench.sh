#!/usr/bin/env bash
# S81U-1: ot_dsdv_vstop exact bench (5 strap sets x 8 seeds) + 3 mutants that must FAIL.  Prints VSTOP_GATE PASS/FAIL.
# SHVC-BENCH 10-18: Verilator, not Icarus: Icarus 12.0 vvp asserts (vthread.cc of_RET_VEC4 `val.size() == wid`) on
# tb_dsdv_vstop with the S81U-1 RTL and the JREG RTL alike, so every run printed golden FAIL (tool, not RTL).
set -u
D=$(cd "$(dirname "$0")/.." && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
T=${1:-$(mktemp -d)}; mkdir -p "$T"
vb() { verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsdv_vstop "$@" \
         "$D/test/tb_dsdv_vstop.sv" "$D/ot_dsdv_vstop.sv"; }
vb --Mdir "$T/v0" -o tb > "$T/build_v0.log" 2>&1 || { echo "VSTOP_GATE FAIL compile"; exit 1; }
bad=0; n=0
for s in 1 2 3 4 5 6 7 8; do
  for ts in "21 20" "ff 00" "e9 e9" "00 00" "ff ff"; do
    set -- $ts; n=$((n + 1))
    "$T/v0/tb" +seed=$s +tap=$1 +sink=$2 | grep -q '^VSTOP PASS' || { echo "golden FAIL seed=$s tap=$1 sink=$2"; bad=1; }
  done
done
for m in 1 2 3; do
  vb -DMUT=$m --Mdir "$T/m$m" -o tb > "$T/build_m$m.log" 2>&1 || { echo "mutant $m BUILD_FAIL"; bad=1; continue; }
  "$T/m$m/tb" +seed=5 +tap=21 +sink=20 > "$T/run_mut$m.log" 2>&1
  if grep -q '^VSTOP PASS' "$T/run_mut$m.log"; then echo "mutant $m NOT detected"; bad=1; else echo "mutant $m detected: $(grep -m1 '^VSTOP' "$T/run_mut$m.log")"; fi
done
verilator --lint-only -Wall "$D/ot_dsdv_vstop.sv" || bad=1
[ $bad = 0 ] && echo "VSTOP_GATE PASS ($n golden runs, 3/3 mutants detected, lint clean)" || echo "VSTOP_GATE FAIL"
exit $bad

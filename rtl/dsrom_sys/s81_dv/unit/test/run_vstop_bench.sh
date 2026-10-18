#!/usr/bin/env bash
# S81U-1: ot_dsdv_vstop exact bench (5 strap sets x 8 seeds) + 3 mutants that must FAIL.  Prints VSTOP_GATE PASS/FAIL.
set -u
D=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
iverilog -g2012 -o "$T/v0" "$D/test/tb_dsdv_vstop.sv" "$D/ot_dsdv_vstop.sv" || { echo "VSTOP_GATE FAIL compile"; exit 1; }
bad=0; n=0
for s in 1 2 3 4 5 6 7 8; do
  for ts in "21 20" "ff 00" "e9 e9" "00 00" "ff ff"; do
    set -- $ts; n=$((n + 1))
    vvp -n "$T/v0" +seed=$s +tap=$1 +sink=$2 | grep -q '^VSTOP PASS' || { echo "golden FAIL seed=$s tap=$1 sink=$2"; bad=1; }
  done
done
for m in 1 2 3; do
  iverilog -g2012 -DMUT=$m -o "$T/m$m" "$D/test/tb_dsdv_vstop.sv" "$D/ot_dsdv_vstop.sv"
  if vvp -n "$T/m$m" +seed=5 +tap=21 +sink=20 | grep -q '^VSTOP PASS'; then echo "mutant $m NOT detected"; bad=1; else echo "mutant $m detected"; fi
done
verilator --lint-only -Wall "$D/ot_dsdv_vstop.sv" || bad=1
[ $bad = 0 ] && echo "VSTOP_GATE PASS ($n golden runs, 3/3 mutants detected, lint clean)" || echo "VSTOP_GATE FAIL"
exit $bad

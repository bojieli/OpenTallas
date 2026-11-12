#!/usr/bin/env bash
# BUS-GEAR-1: S81 x-lane 2:1 gear bench (tb_ot_s81_xlane_gear.sv). Usage (worktree root): run_xlane_bench.sh OUT
# H 0/3/6 relay stations exact (word = TX input delayed 1 + H + 1, zero on non-word edges); MUT 1 (beat order) and
# MUT 3 (no spacing fault) must FAIL.
set -uo pipefail
out=${1:?out}; mkdir -p "$out"; bad=0
src="rtl/common/ot_bus_gear.sv rtl/dsrom_sys/s81_dv/xgear/ot_s81_xlane_gear.sv results/arch/bus_gear_1112/bench/tb_ot_s81_xlane_gear.sv"
for c in "0 0 PASS" "3 0 PASS" "6 0 PASS" "3 1 FAIL" "3 3 FAIL"; do set -- $c; n=h$1_m$2
  iverilog -g2012 -s tb -Ptb.H=$1 -Ptb.MUT=$2 -o "$out/$n.vvp" $src > "$out/$n.build.log" 2>&1 || { echo "$n BUILD FAIL"; bad=1; continue; }
  r=$(vvp -n "$out/$n.vvp" 2>&1 | tee "$out/$n.log" | grep -E 'XGEAR (PASS|FAIL)'); echo "$n expect=$3 :: $r"
  case "$3:$r" in PASS:*"XGEAR PASS"*|FAIL:*"XGEAR FAIL"*) ;; *) bad=1;; esac
done
[ $bad = 0 ] && echo "XLANE BENCH PASS" || { echo "XLANE BENCH FAIL"; exit 1; }

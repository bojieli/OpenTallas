#!/usr/bin/env bash
# HBM-BIND2 (2026-10-25): ot_hbm_b2_beat_tx/rx gate.  run_b2_beat_link.sh OUT   (repo root)
# 5 shapes (W/NV/BEATS/LANE): the L74 group shapes at BEATS 2/3, a non-multiple width, BEATS 4, BEATS 1 (plain pipe).
# MUT 0 must PASS on every shape; MUT 1-4 (beat order, early v, tx misses a close word, rx drops the last beat) must FAIL
# on every shape with BEATS > 1.  Last line: B2_BEAT_LINK_GATE PASS|FAIL.
set -uo pipefail
out=$(realpath -m "${1:?out}"); mkdir -p "$out"; d=rtl/hbm_accel/die_glue/b2; fail=0
for cfg in "2188 4 3 5" "320 3 2 5" "2056 1 2 0" "8 1 3 1" "100 2 4 3" "1491 1 1 2"; do
 set -- $cfg
 for m in 0 1 2 3 4; do
  [ $3 = 1 ] && [ $m != 0 ] && continue
  o="$out/b_$1_$2_$3_$4_m$m"
  iverilog -g2012 -s tb_b2_beat_link -Ptb_b2_beat_link.W=$1 -Ptb_b2_beat_link.NV=$2 -Ptb_b2_beat_link.BEATS=$3 \
    -Ptb_b2_beat_link.LANE=$4 -Ptb_b2_beat_link.MUT=$m -o "$o" $d/tb_ot_hbm_b2_beat_link.sv $d/ot_hbm_b2_beat_link.sv \
    || { echo "BUILD_FAIL $cfg $m"; fail=1; continue; }
  r=$(vvp -n "$o" | grep '^B2_BEAT_LINK'); echo "$r"
  if [ $m = 0 ]; then echo "$r" | grep -q ' PASS$' || fail=1; else echo "$r" | grep -Eq 'errors=[1-9][0-9]* FAIL$' || fail=1; fi
 done
done
[ $fail = 0 ] && echo B2_BEAT_LINK_GATE PASS || { echo B2_BEAT_LINK_GATE FAIL; exit 1; }

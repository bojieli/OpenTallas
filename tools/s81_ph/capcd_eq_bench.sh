#!/bin/bash
# capcd_eq_bench.sh (S-VM-CAPT-CD 2026-10-16): bit-exact equivalence of ctrl_c/dsfd_capt_cd.sv (precomputed armed/!dr_q
# term + ICG-gated t_cd bank) against the frozen 2314b2b4d form, randomized lockstep (rtl/dsrom_sys/s81_ph/test/
# tb_dsfd_capt_cd_eq.sv).  Two DUT views per seed: the simulation model (enable form) and -DSYNTHESIS (the ICG cell
# through a behavioural latch+AND model, i.e. the gated-clock netlist structure).
# usage (source root): tools/s81_ph/capcd_eq_bench.sh <out> "<seeds>" [defines...]
#   define CAPCD_PINREG (S-VM-CAPT-CD2): DUT #(.PINREG(1)), reference fed f_st delayed exactly one ckv edge (+1 ckv)
#   verdict: "CAPCD_BENCH PASS runs=<n>" when every (view, seed) run prints EQ_PASS, else "CAPCD_BENCH FAIL"
set -u
OUT=$1; SEEDS=$2; shift 2
D=(); for x in "$@"; do D+=("-D$x"); done
mkdir -p "$OUT"
SRC="rtl/dsrom_sys/s81_ph/test/dsfd_capt_cd_ref1013.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_cd.sv rtl/dsrom_sys/s81_ph/test/tb_dsfd_capt_cd_eq.sv"
for v in sim syn; do
  extra=(); [ $v = syn ] && extra=(-DSYNTHESIS)
  iverilog -g2012 "${D[@]}" "${extra[@]}" -s tb_dsfd_capt_cd_eq -o "$OUT/tb_$v" $SRC > "$OUT/build_$v.log" 2>&1 \
    || { cat "$OUT/build_$v.log"; echo "CAPCD_BENCH FAIL build $v"; exit 1; }
done
: > "$OUT/summary.txt"
for v in sim syn; do for s in $SEEDS; do
  r=$(vvp -n "$OUT/tb_$v" +SEED=$s +N=200000 2>&1 | tee "$OUT/run_${v}_$s.log" | grep '^CAPCD_EQ cycles' | tail -1)
  echo "$v seed=$s ${r:-NO_VERDICT}" | tee -a "$OUT/summary.txt"
done; done
if grep -v 'EQ_PASS' "$OUT/summary.txt" | grep -q . || ! grep -q . "$OUT/summary.txt"; then echo "CAPCD_BENCH FAIL" | tee -a "$OUT/summary.txt"; exit 1; fi
echo "CAPCD_BENCH PASS runs=$(grep -c EQ_PASS "$OUT/summary.txt")" | tee -a "$OUT/summary.txt"

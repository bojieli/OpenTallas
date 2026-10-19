#!/bin/bash
# HBM-NEXT-P3-SM (10-19): every P = 3 SM bench in one fleet run (Verilator 5.050, the closure daemon's version).
#   bash rtl/hbm_next/sm/tb/run_p3_benches.sh OUT        (FLEET only, via ot-run; ~6 parallel builds)
# lf  = leaf on P separate closed x stores (hnx_rp4lp4_lf)       : P1-3 PASS, P3 MUT1-3 must be CAUGHT
# lfx = leaf on the SHARED x store (-DHNX_XS4; P = 3 -> hnx_xs3) : P1-3 PASS (+P4 regression), P3 MUT1-4 must be CAUGHT
# thr = throughput shape (THR = 1, K = 16 and K = 4) P1 vs P3 on lfx
# lp  = lockstep hnx_rp3lp3x_flat vs hnx_rp3lp3x_flat_lp + landing mutants + region audit
set -u
OUT=$1; mkdir -p "$OUT"
R=$(cd "$(dirname "$0")/../../../.." && pwd); cd "$R"
T=rtl/hbm_next/sm/tb/run_leaf_bench.sh
jobs=()
for p in 1 2 3; do jobs+=("lf $p 0 0 4 12"); done
for m in 1 2 3; do jobs+=("lf 3 $m 0 4 12"); done
for p in 1 2 3 4; do jobs+=("lfx $p 0 0 4 12"); done
for m in 1 2 3 4; do jobs+=("lfx 3 $m 0 4 12"); done
for k in 16 4; do for p in 1 3; do jobs+=("thr$k $p 0 1 $k $k"); done; done
run1() {
  set -- $1; kind=$1; p=$2; m=$3; t=$4; kmin=$5; kmax=$6
  case $kind in lf) d=$OUT/lf; x="";; lfx) d=$OUT/lfx; x="-DHNX_XS4";; thr*) d=$OUT/$kind; x="-DHNX_XS4";; esac
  mkdir -p "$d"
  bash $T "$d" $p $m $t -GKMIN=$kmin -GKMAX=$kmax $x > "$d/summary_p${p}_m${m}_t${t}.txt" 2>&1; rc=$?
  echo "$kind P$p MUT$m THR$t exit $rc: $(tail -1 "$d/summary_p${p}_m${m}_t${t}.txt")"
}
export -f run1; export OUT T
printf '%s\n' "${jobs[@]}" | xargs -P ${NPAR:-6} -I{} bash -c 'run1 "{}"'
mkdir -p "$OUT/lp"; LP_ROOT=$R SIM=verilator VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator} \
  bash rtl/hbm_next/sm/lp/hnx_rp3lp3x_flat_lp_bench.sh "$OUT/lp" > "$OUT/lp/bench_summary.log" 2>&1; echo "LP exit $?: $(tail -1 "$OUT/lp/bench_summary.log")"
rm -rf "$OUT"/lp/obj* "$OUT"/lp/sim*
echo P3_BENCHES_DONE

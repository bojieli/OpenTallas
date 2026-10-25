#!/usr/bin/env bash
# S81/IDXNET (2026-10-25): lep index-network ends (TP4 topk_final + rank-tree Q relay + tm merge), Verilator 5.050.
#   base  tb_s81sl_lep_idxnet seeds 1 / 5, RSLOT 3, TSLOT 3 (PASS)
#   mut   OT_S81SL_LEP_MUT_{IDXDMX,QBEAT,QRL,TPMRG}: each must FAIL
#   regr  run_lep_idx_bench.sh all (H4 tree bench + its mutants + the lep_mu regression: the edited core, IDX_TP 0 path)
# Usage (cwd = repo root): run_lep_idxnet_bench.sh OUTDIR [base|mut|regr|all]
set -u
O=${1:?outdir}; WHAT=${2:-all}; mkdir -p "$O"
SL=rtl/dsrom_sys/s81_dv/slice
bad=0
if [ "$WHAT" != regr ]; then
  # reuse the H4 script's source list / build flags
  eval "$(sed -n '/^V=verilator/,/^D=/p' $SL/test/run_lep_idx_bench.sh)"
  eval "$(sed -n '/^build() {/,/^}/p' $SL/test/run_lep_idx_bench.sh)"
  run() { n=$1; top=$2; exp=$3; re=$4
    "$O/$n/V$top" > "$O/$n.log" 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " "$O/$n.log"); echo "$n: $v"
    echo "$v" | grep -q -E "^$exp $re" || { echo "  $n: expected $exp"; bad=1; }; }
  sha256sum $SRCS $SL/test/tb_s81sl_lep_idxnet.sv > "$O/sources.sha256"
fi
if [ "$WHAT" = base ] || [ "$WHAT" = all ]; then
  for s in 1 5; do build net_s$s tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv -GSEED=$s && run net_s$s tb_s81sl_lep_idxnet PASS lep_idxnet || bad=1; done
  # a ring frame in the cycle right after a Q frame (root, RSLOT 3) / after a tree frame (D6, TSLOT 3), same pair
  build net_r3 tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv -GRSLOT=3 && run net_r3 tb_s81sl_lep_idxnet PASS lep_idxnet || bad=1
  build net_t3 tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv -GTSLOT=3 && run net_t3 tb_s81sl_lep_idxnet PASS lep_idxnet || bad=1
fi
if [ "$WHAT" = mut ] || [ "$WHAT" = all ]; then
  for m in IDXDMX QBEAT QRL TPMRG; do
    build mut_$m tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv +define+OT_S81SL_LEP_MUT_$m && run mut_$m tb_s81sl_lep_idxnet FAIL lep_idxnet || bad=1
  done
fi
if [ "$WHAT" = regr ] || [ "$WHAT" = all ]; then
  bash $SL/test/run_lep_idx_bench.sh $O/regr_h4 all > $O/regr_h4.log 2>&1; tail -14 $O/regr_h4.log
  grep -q "^LEP_IDX_GATE PASS" $O/regr_h4.log || bad=1
fi
[ $bad = 0 ] && echo "LEP_IDXNET_GATE PASS" || echo "LEP_IDXNET_GATE FAIL"
exit $bad

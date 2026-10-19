#!/usr/bin/env bash
# HBM-FAULT 10-17: d4f fault-aggregation tree (22 ot_hbm_fault_leaf + ot_hbm_status_join_fa), 157 source bits, two
# relay seeds; mutants (leaf MUT 1..3, join FMUT 1..3) must FAIL.
set -euo pipefail
out=${1:?output}; mkdir -p "$out"
R="rtl/hbm_accel/die_glue/ot_hbm_fault_leaf.sv rtl/hbm_accel/host_static_20261015/ot_hbm_status_join_fa.sv rtl/hbm_accel/host_static_20261015/ot_hbm_status_join.sv"
for seed in 1017 7; do
  python3 tools/hbm_die_v16/bench_fault_tree_1017.py "$out/tb_$seed.sv" $seed
  for m in L0 L1 L2 L3 F1 F2 F3; do
    t=${m:0:1}; k=${m:1}
    if [ $t = L ]; then P="-Ptb.LMUT=$k"; else P="-Ptb.FMUT=$k"; fi
    [ $seed = 1017 ] || [ $m = L0 ] || continue
    iverilog -g2012 -s tb $P -o "$out/${seed}_$m.vvp" "$out/tb_$seed.sv" $R > "$out/${seed}_$m.build.log" 2>&1
    vvp -n "$out/${seed}_$m.vvp" > "$out/${seed}_$m.log" 2>&1 || true
    if grep -q 'FAULT_TREE PASS' "$out/${seed}_$m.log"; then
      [ $m = L0 ] || { echo "FAULT_TREE_MUTANT_SURVIVED seed=$seed $m"; exit 1; }
      echo "seed=$seed $(grep 'FAULT_TREE PASS' "$out/${seed}_$m.log")"
    else
      [ $m != L0 ] || { head -20 "$out/${seed}_$m.log"; exit 1; }
      echo "FAULT_TREE_MUTANT_REJECTED $m: $(grep -m1 -oE 'FAULT_TREE_FAIL [^ ]+ src=[0-9-]+' "$out/${seed}_$m.log")"
    fi
  done
done

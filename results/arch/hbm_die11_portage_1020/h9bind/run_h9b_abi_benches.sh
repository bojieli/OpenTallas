#!/bin/bash
# HBM-H9BIND 10-20: old-rate h9b controller ABI/calendar benches on the exact die source tree (src = ep6 codex-hbm-die11-1020/src,
# h9b sources byte-identical to the closed view 1aa2ec44b). H9B_TXN = transaction/calendar equivalence vs H9 (K +1 edge, KR RL1),
# RMUT=1 must fail; PC_REFCFG = refresh producer feeding 32 h9b masters vs strap miter + 4 mutants.
set -euo pipefail
B=$1; S=$2   # B = bench work dir, S = die src root
mkdir -p $B/root/results/arch/hbm_pc_cfg_h8_1623/source
cp $B/ot_hbm_r14_stream_pc_strap_h7.sv $B/root/results/arch/hbm_pc_cfg_h8_1623/source/
for p in rtl tools/hbm_die_v16 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2; do
  mkdir -p $B/root/$(dirname $p); ln -sfn $S/$p $B/root/$p; done
cd $B/root
sha256sum rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_h9b.sv
bash tools/hbm_die_v16/bench_pc_cfg_h9b_txn.sh $B/out/txn 0 | tail -2
if bash tools/hbm_die_v16/bench_pc_cfg_h9b_txn.sh $B/out/rmut1 1 > $B/out/rmut1.txt 2>&1; then echo H9B_RMUT1_SURVIVED; exit 1; fi
grep -E 'H9B_TXN FAIL errors=[0-9]+ RMUT=1' $B/out/rmut1.txt | head -1 && echo H9B_RMUT1_REJECTED
bash tools/hbm_die_v16/bench_pc_refresh_cfg.sh $B/out/refcfg
echo H9BIND_ABI_BENCHES_DONE

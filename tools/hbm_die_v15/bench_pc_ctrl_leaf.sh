#!/usr/bin/env bash
# H-DIE 2026-10-15: production-shape bench of the per-PC controller die leaf ot_hbm_svc_pc_ctrl_leaf.
#   bench_pc_ctrl_leaf.sh <out> <mut 0|1> [stack]
# Builds the capacity images (tools/hbm_die_v15/svc_capacity_images_1705.py: 8 SMs x 64 rows on their own four PCs,
# installed with the production installer), then runs the actual SM-stack capacity bench (all 8 SM groups + the 32-leaf
# controller + DRAM fixture at the PHY row/column boundary): every record delivered exact, early-calendar mutant rejected.
# mut=1: the leaf's response identity FIFO pairs a DRAM return with the NEXT pending identity -> must FAIL.
set -euo pipefail
out=${1:?out}; mut=${2:-0}; stack=${3:-2}
d=rtl/hbm_accel/loader/service_native
mkdir -p "$out"
python3 tools/hbm_die_v15/svc_capacity_images_1705.py --stack "$stack" --rows 64 --out "$out/images" > "$out/images.log"
if [ "$mut" = 1 ]; then
  sed 's/response_identity\[response_wp\]<=pending_identity\[pending_rp\]/response_identity[response_wp]<=pending_identity[pending_rp+5'"'"'d1]/' \
    $d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv > "$out/leaf_mut.sv"
  cmp -s "$out/leaf_mut.sv" $d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv && { echo 'mutant not applied'; exit 3; }
  export CFG_LEAF_SRC="$out/leaf_mut.sv"
fi
bash $d/run_ctrl_leaves.sh run_sm_stack_capacity.sh "$out/run" "$out/images" "$stack" 64
grep "SM_STACK_CAPACITY PASS" "$out/run/positive.log"

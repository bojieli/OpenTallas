#!/usr/bin/env bash
# Static IDX.TOPK gate on the actual SW VM slice (H-IDX 2026-10-15). usage: run_topk_static.sh OUT [random_count] [seed]
# MUT0 must PASS; MUT1..5 (rank by score, ties high, lanes skipped, capture early, split write dropped) must FAIL.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); cnt=${2:-24}; seed=${3:-0}; mkdir -p "$out"
python3 tools/hbm_idx_topk_static_vectors.py "$out/vec" "$cnt" "$seed" | tee "$out/vectors.log"
src=(rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_hub_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_rstop_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_rcl_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/hbm_idx_static/tb_idx_topk_static.sv)
rc_all=0
for m in 0 1 2 3 4 5; do
  iverilog -g2012 -s tb_idx_topk_static -Ptb_idx_topk_static.MUT=$m -o "$out/m$m.vvp" "${src[@]}" > "$out/build$m.log" 2>&1
  set +e; (cd "$out/vec" && vvp "$out/m$m.vvp") > "$out/run$m.log" 2>&1; rc=$?; set -e
  grep IDX_TOPK_STATIC "$out/run$m.log" || tail -3 "$out/run$m.log"
  if [ $m = 0 ]; then [ $rc = 0 ] || rc_all=1; else [ $rc != 0 ] || { echo "MUT$m NOT KILLED"; rc_all=1; }; fi
  rm -f "$out/m$m.vvp"
done
sha256sum "${src[@]}" tools/hbm_idx_topk_static_vectors.py > "$out/sources.sha256"
[ $rc_all = 0 ] && echo "IDX_TOPK_STATIC GATE PASS" || { echo "IDX_TOPK_STATIC GATE FAIL"; exit 1; }

#!/usr/bin/env bash
# H-MTP2/idx P-row IDX.TOPK gate on the ACTUAL SW VM slice (v15/v16 ABI). usage: run_topk_rows.sh OUT [P=6] [seed=0] [engine=static|rows]
#   static: the die-bound ot_hbm_idx_topk_static (unchanged); M0 must PASS; engine MUT1..5 and H1 (bench force: heap not
#           reset between rows) must FAIL.
#   rows:   the pipelined P-row successor ot_hbm_idx_topk_rows_static; M0 must PASS; MUT1 (heap not reset between rows),
#           MUT2 (row stride dropped), MUT3 (lane insert rate violated) must FAIL.
# Needs Icarus >= 12 (Icarus 11 leaves the engines' for-loop-reset read pipeline at x).
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); P=${2:-6}; seed=${3:-0}; engine=${4:-static}; mkdir -p "$out"
python3 tools/hbm_idx_topk_rows_vectors.py "$out/vec" "$P" "$seed" 12 "$engine" | tee "$out/vectors.log"
src=(rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_rows_static.sv
 rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_hub_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_rstop_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_rcl_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/hbm_idx_rows/tb_idx_topk_rows.sv)
if [ "$engine" = rows ]; then E=1; vars="M0 M1 M2 M3"; else E=0; vars="M0 M1 M2 M3 M4 M5 H1"; fi
rc_all=0
for v in $vars; do
  m=0; h=0; case $v in M*) m=${v#M};; H*) h=${v#H};; esac
  iverilog -g2012 -s tb_idx_topk_rows -Ptb_idx_topk_rows.ENGINE=$E -Ptb_idx_topk_rows.MUT=$m -Ptb_idx_topk_rows.MUTH=$h \
    -o "$out/$v.vvp" "${src[@]}" > "$out/build_$v.log" 2>&1
  set +e; (cd "$out/vec" && vvp "$out/$v.vvp") > "$out/run_$v.log" 2>&1; rc=$?; set -e
  echo "$v: $(grep IDX_TOPK_ROWS "$out/run_$v.log" || tail -1 "$out/run_$v.log")"
  if [ $v = M0 ]; then [ $rc = 0 ] || rc_all=1; else [ $rc != 0 ] || { echo "$v NOT KILLED"; rc_all=1; }; fi
  rm -f "$out/$v.vvp"
done
sha256sum "${src[@]}" tools/hbm_idx_topk_static_vectors.py tools/hbm_idx_topk_rows_vectors.py > "$out/sources.sha256"
[ $rc_all = 0 ] && echo "IDX_TOPK_ROWS GATE PASS ($engine)" || { echo "IDX_TOPK_ROWS GATE FAIL ($engine)"; exit 1; }

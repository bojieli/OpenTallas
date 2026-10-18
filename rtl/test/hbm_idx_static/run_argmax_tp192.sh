#!/usr/bin/env bash
# Static ARGMAX.LOCAL gate on the actual SW VM slice (H-IDX 2026-10-15). usage: run_argmax_static.sh OUT [seed]
# MUT0 must PASS; MUT1 (id offset), MUT2 (capture early), MUT3 (id word not written) must FAIL.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); seed=${2:-0}; mkdir -p "$out"
src=(rtl/hbm_accel/generic/ot_hbm_argmax_static.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
 physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv
 rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_hub_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_rstop_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_rcl_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/hbm_idx_static/tb_argmax_static.sv)
rc_all=0
for tc in 96:3:0 192:0:0 192:127:0 192:128:0 192:191:0 192:191:1; do
 IFS=: read -r tp rank rmut <<< "$tc"
 tag=tp${tp}_rank${rank}_mut${rmut}
 mkdir -p "$out/$tag"
 python3 tools/hbm_argmax_static_vectors.py "$out/$tag/vec" "$seed" "$rank" > "$out/$tag/vectors.log"
 iverilog -g2012 -s tb_argmax_static -Ptb_argmax_static.TP=$tp -Ptb_argmax_static.DIE_RANK=$rank -Ptb_argmax_static.RANK_MUT=$rmut -o "$out/$tag/run.vvp" "${src[@]}" > "$out/$tag/build.log" 2>&1
 set +e
 (cd "$out/$tag/vec" && vvp "$out/$tag/run.vvp") > "$out/$tag/run.log" 2>&1
 rc=$?
 set -e
 grep ARGMAX_STATIC "$out/$tag/run.log" || tail -3 "$out/$tag/run.log"
 if [ "$rmut" = 0 ]; then
  [ "$rc" = 0 ] && grep -q 'errors0' "$out/$tag/run.log" || rc_all=1
 else
  [ "$rc" != 0 ] && grep -q 'static ARGMAX on actual SW slice mismatch' "$out/$tag/run.log" || rc_all=1
 fi
 rm -f "$out/$tag/run.vvp"
done
sha256sum "${src[@]}" tools/hbm_argmax_static_vectors.py > "$out/sources.sha256"
[ "$rc_all" = 0 ] && echo ARGMAX_TP192_GATE_PASS || { echo ARGMAX_TP192_GATE_FAIL;exit 1; }

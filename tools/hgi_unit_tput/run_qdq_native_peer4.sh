#!/bin/bash
# Four actual qpin4 production-record/golden endpoints on native VM group1.
# Fixed common VM source64fced1f9, core833.333/VM1111.111ps; no repricing.
# Usage: run_qdq_native_peer4.sh VECTORS OUT; MUT=0/1/2, PHASE=61/487.
set -euo pipefail
vec=$(realpath "$1"); out=$(realpath -m "$2"); mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
B2="$out/native_common/b2"
mkdir -p "$B2" "$out/native_common"
common_commit=${NATIVE_VM_COMMIT:-64fced1f9}
if [ -n "${NATIVE_COMMON_DIR:-}" ]; then
 (cd "$NATIVE_COMMON_DIR" && sha256sum -c manifest.sha256)
 cp -a "$NATIVE_COMMON_DIR"/. "$out/native_common"/
else
for f in ot_vms_bank ot_vms_hub ot_vms_rstop ot_vms_rcl ot_vms_star ot_vms_relay ot_vms_slice; do
 git show "$common_commit:rtl/hbm_accel/generic/vm/b2/$f.sv" > "$B2/$f.sv"
done
for f in ot_hbm_b2_lane_cdc ot_hbm_b2_su_vm4; do
 git show "$common_commit:rtl/hbm_accel/generic/adapters/native_b2/su_quadrant/$f.sv" > "$out/native_common/$f.sv"
done
git show "$common_commit:rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv" > "$out/native_common/ot_hbm_accel_cdc_fifo_p2.sv"
fi
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
     rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
src=("${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
     rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv
     rtl/lib/ot_rst_relay.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_lq.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr_one_s2.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr_retire.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr_mix.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_core.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_asm.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_wr.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_q.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_q_pin4.sv
     $B2/ot_vms_bank.sv $B2/ot_vms_hub.sv $B2/ot_vms_rstop.sv $B2/ot_vms_rcl.sv $B2/ot_vms_star.sv $B2/ot_vms_relay.sv $B2/ot_vms_slice.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/hbm_accel/generic/qw/ot_hgi_qdq_native_peer4.sv "$out/native_common/ot_hbm_b2_lane_cdc.sv" "$out/native_common/ot_hbm_b2_su_vm4.sv" "$out/native_common/ot_hbm_accel_cdc_fifo_p2.sv" rtl/test/hbm_accel/generic/tb_hgi_qdq_native_peer4.sv)
# Optional immutable q8e baseline, to distinguish actual SPAN1 from old SPAN0 diagnostics.
if [ -n "${QDQ_BASELINE_DIR:-}" ];then
 (cd "$QDQ_BASELINE_DIR" && sha256sum -c manifest.sha256)
 for i in "${!src[@]}";do
  case "${src[$i]}" in
   rtl/hbm_accel/generic/qw/ot_hgi_qdq_core.sv) src[$i]="$QDQ_BASELINE_DIR/ot_hgi_qdq_core.sv" ;;
   rtl/hbm_accel/generic/qw/ot_hgi_qdq_wr.sv) src[$i]="$QDQ_BASELINE_DIR/ot_hgi_qdq_wr.sv" ;;
  esac
 done
fi
m=${MUT:-0}
"$VL" --binary --timing -O2 -CFLAGS -O0 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT="$m" -GFASTFIN="${FASTFIN:-0}" -GFRONTFAST="${FRONTFAST:-0}" --top-module tb_hgi_qdq_native_peer4 -Mdir "$out/obj" -o sim "${src[@]}" > "$out/build.log" 2>&1 || { tail -30 "$out/build.log";exit 2; }
set +e
"$out/obj/sim" +DIR="$vec" +PHASE="${PHASE:-61}" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"

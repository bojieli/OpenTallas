#!/bin/bash
# FUSED.QDQ_* B2 QUARTER throughput bench (el1011-qdqtput): ot_hgi_qdq_q on the B2 VM slice's local 8-lane group.
# usage (from the repo root): tools/hgi_unit_tput/run_qdq_q.sh <vectors dir> <out dir>
# env: S (relay stages each way, default 1), VERILATOR
# The B2 slice RTL (rtl/hbm_accel/generic/vm/b2) is taken from the tree, or from origin/claude/el1011-hbm-b2-vm until it
# lands on main (provisional port, SPEC.md v0.1 sec 2a).
set -euo pipefail
vec=$(realpath "$1"); out=$(realpath -m "$2"); mkdir -p "$out"
VL=${VERILATOR:-verilator}
B2=rtl/hbm_accel/generic/vm/b2
if [ ! -f $B2/ot_vms_slice.sv ]; then
  mkdir -p "$out/b2"; for f in ot_vms_bank ot_vms_hub ot_vms_rstop ot_vms_rcl ot_vms_star ot_vms_relay ot_vms_slice; do
    git show origin/claude/el1011-hbm-b2-vm:$B2/$f.sv > "$out/b2/$f.sv"; done; B2="$out/b2"
fi
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
     rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
src=("${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
     rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv
     rtl/lib/ot_rst_relay.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_lq.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_q.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_q_pin4.sv
     $B2/ot_vms_bank.sv $B2/ot_vms_hub.sv $B2/ot_vms_rstop.sv $B2/ot_vms_rcl.sv $B2/ot_vms_star.sv $B2/ot_vms_relay.sv $B2/ot_vms_slice.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/test/hbm_accel/generic/tb_hgi_qdq_q_tput.sv)
for m in 0 1 2; do
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m -GS=${S:-1} ${QDQ_G:-} \
    --top-module tb_hgi_qdq_q_tput -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1 &
done
wait
for m in 0 1 2; do
  set +e; "$out/m$m.obj/sim" +DIR="$vec" > "$out/m$m.log" 2>&1; rc=$?; set -e
  echo "$rc" > "$out/m$m.rc"
done
ok=1
grep -q "PASS HGI_QDQ_Q_TPUT" "$out/m0.log" || ok=0
for m in 1 2; do grep -q "PASS HGI_QDQ_Q_TPUT" "$out/m$m.log" && ok=0; done
[ $ok = 1 ] && echo "QDQ_Q_TPUT GATE PASS (m0 PASS, m1/m2 FAIL)" | tee "$out/gate" || { echo "QDQ_Q_TPUT GATE FAIL" | tee "$out/gate"; exit 1; }

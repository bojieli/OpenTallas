#!/bin/bash
# TOKSIM-HBM-su 10-19: FUSED.QDQ_FP8 span on the d4g-bound hb_quant_NW master ot_hgi_qdq_host_split #(RL7,WC4,COMPACT1)
# (lockstep vs the monolith, golden bank writes). Run from the source root. usage: run_qdq_span.sh OUT
set -euo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
 physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_split.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 tools/hbm_static/toksim_su/sfu/tb_toksim_qdq_split.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$VL" --version > "$out/verilator.txt"
"$VL" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=0 --top-module tb_toksim_qdq_split -Mdir "$out/obj" -o sim "${src[@]}" > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 1; }
V=tools/hgi_unit_tput/vectors
"$out/obj/sim" +DIR=$V/qdq1 +PROGRAM=$V/qdq1/program.hex > "$out/qdq1.log" 2>&1 || true
"$out/obj/sim" +DIR=$V/qdqvec +PROGRAM=results/hbm_static_quant_1015/compact_fixture.hex > "$out/qdqvec.log" 2>&1 || true
# mutant witness: split built with RL=5 (LG/transport edges not priced) must fail
"$VL" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=2 --top-module tb_toksim_qdq_split -Mdir "$out/obj2" -o sim "${src[@]}" > "$out/build2.log" 2>&1 && { "$out/obj2/sim" +DIR=$V/qdq1 +PROGRAM=$V/qdq1/program.hex > "$out/qdq1_mut2.log" 2>&1; echo "rc=$?" >> "$out/qdq1_mut2.log"; } || true
grep -h "PASS\|TOKSIM\|FAIL" "$out"/qdq1.log "$out"/qdqvec.log "$out"/qdq1_mut2.log | head
rm -rf "$out/obj" "$out/obj2"

#!/bin/bash
# HBM-SU3 10-17: pgslice_lg stream-domain reset synchroniser bench. usage: su_pgslice_lg_rsync_run.sh OUT [MUT] [EDGES]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; edges=${3:-1500}; mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su
iverilog -g2012 -s tb_hbm_su_pgslice_lg_rsync -Ptb_hbm_su_pgslice_lg_rsync.MUT=$mut -Ptb_hbm_su_pgslice_lg_rsync.EDGES=$edges \
 -o "$out/rsync.vvp" \
 $S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_lane_pinreg.sv \
 $S/arithmetic/ot_hbm_su_static_side.sv $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv $S/ot_hbm_su_static_vm_ports.sv \
 $S/programme/multirate_bridge.sv $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_pg_lg_tap.sv \
 $S/top/ot_hbm_su_static_pgslice_lg.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv \
 rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv \
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv \
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_su_pgslice_lg_rsync.sv
vvp -n "$out/rsync.vvp" | tee "$out/bench.log" | tail -20

#!/bin/bash
# HH-6 10-18: Verilator 5.050 lint of the pgslice + qcore_r5 with PRETREE=1 (the die parameters + the widening).
set -euo pipefail
cd "$(dirname "$0")/../.."
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$VL" ] || VL=verilator
S=rtl/hbm_accel/generic/adapters/static_su
F="$S/reduction/ot_hbm_su_red_pretree.sv $S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_lane_pinreg.sv  $S/arithmetic/ot_hbm_su_static_side.sv $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv $S/ot_hbm_su_static_vm_ports.sv  $S/programme/multirate_bridge.sv $S/top/ot_hbm_su_static_pgslice.sv  rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv  rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv  rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv  rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
$VL --version
$VL --lint-only -Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN -DOT_FP_DATA_NORST --top-module ot_hbm_su_static_pgslice  -GPRETREE=1 -GCOLLPORT=1 -GRF_LOCAL=1 -GPIN_REG=1 -GPG_RSYNC=1 $F 2>&1 | grep -E "%Error|pretree|PRETREE" | head -20 || true
$VL --lint-only -Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -DOT_FP_DATA_NORST --top-module ot_hbm_su_static_qcore_r5 -GPRETREE=1  $S/reduction/ot_hbm_su_red_pretree.sv $S/top/ot_hbm_su_static_qcore_r5.sv $S/reduction/ot_hbm_su_reduce_static.sv  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v 2>&1 | grep -E "%Error|%Warn" | head -20 || true
echo LINT_DONE

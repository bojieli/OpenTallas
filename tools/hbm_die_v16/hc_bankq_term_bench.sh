#!/bin/bash
# F-T 2026-10-19: Verilator 5.050 bench of ot_hbm_hc_bankq_term_static vs die canonical terminal (scoped hcb.sv).
#   hc_bankq_term_bench.sh TMUT   (run from the source root; 0 = production must PASS, 3 = mutant must FAIL)
set -o pipefail
M=${1:-0}; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
G=rtl/hbm_accel/generic/peers/static_hc
SRCS="physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
rtl/hbm_accel/die_glue/scoped_d4g/hcb.sv
$G/ot_hbm_hc_bank_static.sv $G/ot_hbm_hc_bankq_term_static.sv
rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv
$G/tb/tb_hc_bankq_term_eq.sv"
$V --version
O=obj_term_m$M; rm -rf $O
$V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hc_bankq_term_eq +define+TMUT=$M -Mdir $O $SRCS > $O.build.log 2>&1 || { tail -30 $O.build.log; echo BUILD_FAIL; exit 2; }
./$O/Vtb_hc_bankq_term_eq

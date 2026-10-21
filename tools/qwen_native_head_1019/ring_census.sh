#!/bin/bash
set -euo pipefail
mkdir -p census
yosys -p 'read_verilog -sv -DSYNTHESIS rtl/qwen_dv/qfd_dv_head_native_b64.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1_bb.v physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v; hierarchy -check -top qfd_dv_lane_h_native_b64; synth -top qfd_dv_lane_h_native_b64 -flatten -noabc; write_json census/netlist.json; stat' >census/yosys.log 2>&1

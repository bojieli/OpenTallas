#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p control_equiv
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint --top-module tb_head_control_equiv --Mdir control_equiv/obj rtl/test/qwen_dv/tb_head_control_equiv.sv rtl/qwen_dv/qfd_dv_head_native_b64.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v > control_equiv/build.log 2>&1
control_equiv/obj/Vtb_head_control_equiv | tee control_equiv/positive.log

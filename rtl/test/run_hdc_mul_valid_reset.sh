#!/bin/bash
set -e
iverilog -g2012 -s tb_mul_valid_reset -o mul_reset.vvp rtl/test/tb_hdc_mul_valid_reset.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fpu.sv > mul_reset_compile.log 2>&1
vvp mul_reset.vvp

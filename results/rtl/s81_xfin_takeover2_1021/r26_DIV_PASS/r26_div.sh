#!/bin/bash
set -euo pipefail
K=$1
R=$(pwd)
SOURCES="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v"
case $K in
div_native)
 top=xfin_div_leaf
 bash census.sh "$K" "$top" - $SOURCES diagnostics/fp_leaf.sv
 ;;
div_equiv)
 kind=tbd
 cd src
 O="$R/out_$K"; mkdir -p "$O"
 "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module "$kind" -Mdir "$O/obj" $SOURCES "diagnostics/r8_$kind.sv" > "$O/build.log" 2>&1
 "$O/obj/V$kind" > "$O/run.log" 2>&1
 cat "$O/run.log"
 grep -q 'EQ_DIV done bad=0' "$O/run.log"
 if [ "$K" = mul_equiv ]; then grep -q 'badr=0' "$O/run.log"; fi
 ;;
esac

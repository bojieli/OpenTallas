#!/bin/bash
# Build + run the oneshot lockstep bench (Verilator 5 --binary --timing).  Usage: bench_oneshot.sh <src> <out> <tag> -G... 
src=$1; out=$2; tag=$3; shift 3
mkdir -p $out/$tag; cd $src
M=physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v
verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_oneshot_f12_lockstep -Mdir $out/$tag/obj "$@" \
  rtl/rom/ot_rom_oneshot_allreduce.sv rtl/hbm_accel/qwen/fmax/ot_rom_oneshot_die_f12.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv $M \
  rtl/test/hbm_accel_qwen/fmax/tb_oneshot_f12_lockstep.sv > $out/$tag/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $out/$tag/build.log; exit 1; }
$out/$tag/obj/Vtb_oneshot_f12_lockstep > $out/$tag/run.log 2>&1
tail -4 $out/$tag/run.log

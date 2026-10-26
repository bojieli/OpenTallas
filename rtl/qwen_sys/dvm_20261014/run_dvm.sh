#!/bin/bash
# Build and run a distributed-x-slice bench under Verilator 5.050 (--timing).
# Usage (repository root): run_dvm.sh <out_dir> <top: tb_qwen_me_dvm_w12 | tb_qfd_xdvm_prod> [-Gparam=value ...]
out=$1; top=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/dvm_20261014
F="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv
   rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_qwen_rom_tile_w12.sv
   rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_matvec.sv
   rtl/lib/ot_rst_pipe.sv $D/ot_qfd_xslice.sv $D/ot_qwen_me_array_dvm_w12.sv $D/$top.sv"
mkdir -p $out
$V --binary --timing -j ${JOBS:-16} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 \
   --top-module $top --prefix Vtb --Mdir $out/obj "$@" $F -o tb -CFLAGS -O1 > $out/build.log 2>&1 || { echo BUILD_FAIL; grep -m20 -i "%Error" $out/build.log; exit 2; }
$out/obj/tb > $out/run.log 2>&1; rc=$?
grep -E "^(PASS|FAIL)" $out/run.log | head -25
exit $rc

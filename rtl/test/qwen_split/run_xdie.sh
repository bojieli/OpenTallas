#!/bin/bash
# run_xdie.sh OUTDIR [-Gparams...] : compute-die x network exactness bench (repo root; Verilator 5.050 --binary)
out=$1; shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/qwen_split/gen_xdie_array.py >/dev/null || exit 3
F="rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_qwen_rom_tile_w12.sv rtl/hdc/ot_hdc_matvec.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
   rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/physical/ot_qwen_tile_lsl.sv rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv
   rtl/qwen_split/ot_qwen_xdie_net.sv rtl/qwen_split/ot_qwen_me_array_xdie_w12.sv rtl/test/qwen_split/tb_qwen_xdie_array.sv"
mkdir -p $out
$V --binary --timing -j ${JOBS:-8} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
   --top-module tb_qwen_xdie_array "$@" --Mdir $out/obj $F > $out/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $out/build.log; exit 2; }
$out/obj/Vtb_qwen_xdie_array | tee $out/result.txt | grep -E "PASS|FAIL" | tail -3

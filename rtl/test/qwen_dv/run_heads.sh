#!/bin/bash
# Q-DV column-head bench (tb_qfd_dv_heads): Verilator 5.050 --timing.  Usage (repository root):
#   rtl/test/qwen_dv/run_heads.sh <out_dir> [-GMUT=8|9 ...]
out=$1; shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/dvm_20261014
F="rtl/qwen_dv/qfd_dv_slice.sv rtl/qwen_dv/qfd_dv_redstn.sv rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_scalar.sv
   rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_heads.sv
   rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv
   rtl/hdc/ot_hdc_vreduce.sv rtl/physical/ot_hdc_vred_pending_guard.sv rtl/hdc/ot_hdc_sfu_q.sv
   rtl/test/full_sm_service/sram_models.sv rtl/test/hbm_rf_visibility/scale_sram_model.sv
   rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv
   rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_qwen_rom_tile_w12.sv
   rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_matvec.sv
   rtl/lib/ot_rst_pipe.sv $D/ot_qfd_xslice.sv $D/ot_qwen_me_array_dvm_w12.sv rtl/test/qwen_dv/tb_qfd_dv_heads.sv"
mkdir -p $out
$V --binary --timing -j ${JOBS:-16} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 \
   --top-module tb_qfd_dv_heads --prefix Vtb --Mdir $out/obj "$@" $F -o tb -CFLAGS -O1 > $out/build.log 2>&1 \
   || { echo BUILD_FAIL; grep -m20 -i "%Error" $out/build.log; exit 2; }
$out/obj/tb > $out/run.log 2>&1; rc=$?
grep -E "^(PASS|FAIL)" $out/run.log | head -12
exit $rc

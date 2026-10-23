#!/bin/bash
# QDIE5-TLD consumer bench (tb_qdie5_tld_chain.sv), Verilator 5.050 (the closure daemon's version), from the repo root.
#   [SHAPE=0/1/2] [PLUSARGS="+K0=k +RUNVAR=3/5"] run_tld_chain.sh WORK VAR NS FX TRACE
#     FX    = mk_fixture.sh output (images/ + fixture/s<k>/expected.hex)
#     TRACE = producer trace of the release tt_ctlm cpub39_1 (results/arch/qdie5_tld_1022/producer/trace_calr2.txt.gz)
#   VAR 0 must print TLD_CHAIN PASS; VAR 1..5 must print TLD_CHAIN FAIL.
set -u
W=$(mkdir -p "$1" && cd "$1" && pwd); VAR=$2; NS=$3; FX=$(cd "$4" && pwd); TR=$5
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
[ "${BUILD_ONLY:-0}" = 1 ] || case $TR in *.gz) zcat "$TR" > "$W/trace.txt"; TR=$W/trace.txt;; esac
BD=results/arch/qdie5_tld_1022/bench
SRCS="rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv
 rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/physical/ot_hdc_vred_pending_guard.sv
 rtl/test/full_sm_service/sram_models.sv rtl/test/hbm_rf_visibility/scale_sram_model.sv rtl/qwen_dv/qfd_dv_heads.sv
 rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/lib/ot_rst_pipe.sv rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/qfd_dv_redstn2.sv
 rtl/qwen_dv/qfd_dv_scalar2.sv rtl/test/qwen_dv/safe_storage/sram_model.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv rtl/qwen_dv/qfd_dv_slice2_faces.sv
 rtl/qwen_dv/qfd_dv_slice_tload.sv rtl/qwen_dv/qfd_dv_table_rom_loader.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 $BD/tb_qdie5_tld_chain.sv"
sha256sum $SRCS > "$W/srcs.sha256"
[ -x "$W/obj/Vtb_qdie5_tld_chain" ] && cmp -s "$W/srcs.sha256" "$W/obj/srcs.sha256" || { "$V" --binary --timing -O2 -j ${VJOBS:-2} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 \
  -GNS=$NS -GSHAPE=${SHAPE:-2} -GVAR=$VAR --top-module tb_qdie5_tld_chain $SRCS -Mdir "$W/obj" > "$W/build.log" 2>&1 \
  || { grep -m20 '%Error' "$W/build.log"; echo "TLD_CHAIN BUILD_FAIL VAR=$VAR"; exit 3; }; cp "$W/srcs.sha256" "$W/obj/srcs.sha256"; }
[ "${BUILD_ONLY:-0}" = 1 ] && { echo "TLD_CHAIN BUILT VAR=$VAR"; exit 0; }
"$W/obj/Vtb_qdie5_tld_chain" +TRACE="$TR" +FX="$FX/fixture" +OT_ROM_DIR="$FX/images" ${PLUSARGS:-} > "$W/run${RUNTAG:-}.log" 2>&1
grep -E "^TRACE|^PRODUCER|^SLICE|TLD_[A-Z_]+ " "$W/run${RUNTAG:-}.log" | head -60
grep -o "TLD_CHAIN [A-Z_]*.*" "$W/run${RUNTAG:-}.log" | tail -1

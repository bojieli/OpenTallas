#!/bin/bash
set -uo pipefail
out=$1
mut=${2:-0}
mkdir -p "$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j "${JOBS:-8}" -O1 --x-assign 0 --x-initial 0 \
  --output-split 20000 --output-split-cfuncs 5000 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  +define+KVD_Q_FP32=1 --top-module tb_qkh_head_native -GMUT="$mut" \
  --Mdir "$out/obj" -o tb \
  rtl/test/qwen_split/tb_qkh_head_native.sv rtl/qwen_sys/split_20261014/ot_qkh_head_native.sv \
  rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv rtl/hdc/nearhbm/ot_qkh_subtiles.sv \
  rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv > "$out/build.log" 2>&1 || {
    tail -20 "$out/build.log"; exit 2;
  }
"$out/obj/tb" > "$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
exit "$rc"

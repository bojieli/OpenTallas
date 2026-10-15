#!/bin/bash
set -eu
out=$1
mut=${2:-0}
mode=${3:-normal}
mkdir -p "$out"
iverilog -g2012 -s tb_qfd_xs_leaf_capture -Ptb_qfd_xs_leaf_capture.MUT="$mut" -o "$out/sim" rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_face_masters.sv rtl/qwen_sys/dvm_extcap_20261015/qfd_xs_leaf_capture.sv rtl/qwen_sys/dvm_extcap_20261015/tb_qfd_xs_leaf_capture.sv > "$out/build.log" 2>&1 || { cat "$out/build.log";exit 2; }
set +e
if [ "$mode" = suite ];then
 vvp "$out/sim" > "$out/run.log" 2>&1;rc=$?;cat "$out/run.log";[ "$rc" = 0 ] || exit "$rc"
 vvp "$out/sim" +early > "$out/early.log" 2>&1;rc=$?;cat "$out/early.log";[ "$rc" = 0 ] || exit "$rc"
 vvp "$out/sim" +drop_clock > "$out/drop_clock.log" 2>&1;rc=$?;cat "$out/drop_clock.log";exit "$rc"
elif [ "$mode" != normal ];then vvp "$out/sim" +"$mode" > "$out/run.log" 2>&1;else vvp "$out/sim" > "$out/run.log" 2>&1;fi
rc=$?
cat "$out/run.log"
exit "$rc"

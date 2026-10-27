#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
E=/srv/opentallas-scratch2/claude/codex-xh-consumer-1027
T=/srv/opentallas-scratch2/claude/codex-qc-xhead-1027/tree
cd "$E"
verilator --cc --exe --build -O1 -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHCONCAT +define+OT_S8_SIM --top-module tb --prefix Vtb -Mdir "$E/obj" "$T/rtl/test/qwen_dv/main2.cpp" "$E/tb.sv" "$E/consumer.sv" "$T/rtl/qwen_dv/s5/s8/qfd_dv_s8_tap_bounded.sv" "$T/rtl/qwen_dv/s5/s8/qfd_dv_s8_tap_bounded_helpers.sv" "$T/rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv" "$T/rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv" "$T/rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv" "$T/rtl/lib/ot_rst_relay.sv" > "$E/build.log" 2>&1

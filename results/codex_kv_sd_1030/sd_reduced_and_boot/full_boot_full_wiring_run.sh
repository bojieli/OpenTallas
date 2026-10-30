#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-kv-sd-1030
iverilog -g2012 -s tb -o "$R/full_boot_full_wiring/run.vvp" "$R/full_boot_full_wiring/tb.sv" "$R/full_boot_full_wiring/top.sv" "$R/full_boot_full_wiring/controls.sv" "$R/ca_data1.sv" "$R/sdpg_diamond/rtl/ot_dp_clk_landing.sv" "$R/sdpg_diamond/rtl/ot_meso_fifo.sv" "$R/sdpg_diamond/rtl/bind_cells.sv" "$R/bindbase/rtl/qwen_sys/split_20261014/qkd_pll_analog_model.sv" >"$R/full_boot_full_wiring/compile.log" 2>&1
vvp -M "$R/vpi_heartbeat" -m heartbeat "$R/full_boot_full_wiring/run.vvp" >"$R/full_boot_full_wiring/result.log" 2>&1

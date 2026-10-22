#!/bin/bash
set -euo pipefail
work=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_ring --Mdir "$work/obj" rtl/test/qwen_dv/safe_scalar_reset/tb_ring.sv rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv > "$work/build.log" 2>&1
"$work/obj/Vtb_ring"

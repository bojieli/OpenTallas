#!/bin/bash
set -eu
cd "$(dirname "$0")/../.."
T=${1:?baseline source tree}; O=${2:?unique output dir}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary -O2 -j 8 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_xhead3 "$T/rtl/lib/ot_rst_relay.sv" "$T/rtl/lib/ot_rst_pipe.sv" "$T/rtl/hdc/ot_hdc_delay.sv" rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv tools/qwen_fault_split/tb_xhead3.sv -Mdir "$O/obj" > "$O/build.log" 2>&1
for cid in 0 5 22 63; do
 "$O/obj/Vtb_xhead3" +seed=1 +cid=$cid +cycles=150000 > "$O/run_$cid.log" 2>&1
 grep 'S5_XH3_EQ PASS' "$O/run_$cid.log"
done

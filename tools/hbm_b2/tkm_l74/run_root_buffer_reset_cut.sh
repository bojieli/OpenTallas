#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");mkdir -p "$o"
flat=rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/cb21/ot_hgi_coll_tkm_tp192_root_core.sv
if [ -f "$flat" ];then
 python3 tools/hbm_b2/tkm_l74/extract_root_buffer_reset_cut.py "$flat" "$o/root_buffer_reset_cut.sv"
else
 cp tools/hbm_b2/tkm_l74/root_buffer_reset_cut.sv "$o/root_buffer_reset_cut.sv"
fi
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j 2 -Wno-fatal --top-module tb_root_buffer_reset_cut --Mdir "$o/obj" tools/hbm_b2/tkm_l74/tb_root_buffer_reset_cut.sv "$o/root_buffer_reset_cut.sv" rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_buffer.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$o/build.log" 2>&1
"$o/obj/Vtb_root_buffer_reset_cut" > "$o/run.log" 2>&1
cat "$o/run.log"

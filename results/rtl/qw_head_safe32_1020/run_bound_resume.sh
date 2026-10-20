#!/bin/bash
set -eu
O="$PWD/results/rtl/qw_head_safe32_1020/bound_r3"
mkdir -p "$O"
sha256sum results/rtl/qw_head_safe32_1020/bound_r1/bit_generic.json > "$O/input.sha256"
python3 results/rtl/qw_head_safe32_1020/bound_head_netlist.py results/rtl/qw_head_safe32_1020/bound_r1/bit_generic.json --top ot_qfd_tt_ctlm_static_hr_safe32 --name ot_qfd_tt_ctlm_static_hr_safe32_native32 --out "$O/native32.v" --helpers "$O/native32_helpers.sv" --record "$O/record.json" --load-cap 16 --transparent-inverters --retain-all-comb --shared-helpers --fuse-ao > "$O/generation.log" 2>&1

#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
yosys -p "read_verilog -sv -DSYNTHESIS rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv; hierarchy -check -top qfd_dv_s6_tap; synth -top qfd_dv_s6_tap -flatten -noabc -nofsm -noshare; write_json $out/tap.json" > "$out/yosys.log" 2>&1
python3 tools/qwen_dv/ctlm6_bound_macro.py "$out/tap.json" --top qfd_dv_s6_tap --name qfd_dv_s8_tap_bounded --out "$out/qfd_dv_s8_tap_bounded.sv" --helpers "$out/qfd_dv_s8_tap_bounded_helpers.sv" --record "$out/source_record.json" --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb

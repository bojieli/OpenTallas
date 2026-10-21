#!/bin/bash
set -eu
O="$PWD/results/rtl/qw_head_safe32_1020/bound_r1"
mkdir -p "$O"
printf 'read_json /input/generic.json\nhierarchy -check -top ot_qfd_tt_ctlm_static_hr_safe32\nsynth -top ot_qfd_tt_ctlm_static_hr_safe32 -flatten -noabc -nofsm -noshare\ndffunmap\nwrite_json /out/bit_generic.json\n' > "$O/bit_generic.ys"
docker run --rm -v "$PWD/results/rtl/qw_head_safe32_1020/generate_r2:/input:ro" -v "$O:/out" openroad/orfs:latest yosys -s /out/bit_generic.ys > "$O/prepare.log" 2>&1
python3 results/rtl/qw_head_safe32_1020/bound_head_netlist.py "$O/bit_generic.json" --top ot_qfd_tt_ctlm_static_hr_safe32 --name ot_qfd_tt_ctlm_static_hr_safe32_native32 --out "$O/native32.v" --helpers "$O/native32_helpers.sv" --record "$O/record.json" --load-cap 16 --transparent-inverters --retain-all-comb --shared-helpers --fuse-ao > "$O/generation.log" 2>&1

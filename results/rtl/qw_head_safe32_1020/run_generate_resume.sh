#!/bin/bash
set -eu
O="$PWD/results/rtl/qw_head_safe32_1020/generate_r5"
mkdir -p "$O"
# Preserve r2 frontend and budget failure; consume exact cached generic source.
sha256sum results/rtl/qw_head_safe32_1020/generate_r2/generic.json > "$O/input.sha256"
python3 results/rtl/qw_head_safe32_1020/replicate_controls.py results/rtl/qw_head_safe32_1020/generate_r2/generic.json "$O/native32.json" --top ot_qfd_tt_ctlm_static_hr_safe32 --max-added-ff 0 > "$O/generation.log" 2>&1
printf 'read_json /out/native32.json\nwrite_verilog /out/native32.v\n' > "$O/write.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/write.ys > "$O/write.log" 2>&1

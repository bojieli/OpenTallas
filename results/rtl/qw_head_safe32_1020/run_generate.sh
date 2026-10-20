#!/bin/bash
set -eu
O="$PWD/results/rtl/qw_head_safe32_1020/generate"
mkdir -p "$O"
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" openroad/orfs:latest yosys -s /src/results/rtl/qw_head_safe32_1020/prepare_generic.ys > "$O/prepare.log" 2>&1
python3 results/rtl/qw_head_safe32_1020/replicate_controls.py "$O/generic.json" "$O/native32.json" --top ot_qfd_tt_ctlm_static_hr_safe32 > "$O/generation.log" 2>&1
printf 'read_json /out/native32.json\nwrite_verilog -noattr /out/native32.unqualified.v\n' > "$O/write.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/write.ys > "$O/write.log" 2>&1

#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
source physical/qwen_die_masters/cfg/hgi_quant_vm_pd50.env
sources=()
for src in $SRCS;do sources+=(--source "$src");done
python3 tools/run_abi3_physical.py --view asap7 --top "$TOP" "${sources[@]}" "${PARAMS[@]}" --stages synth --clock-port clk --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner TC --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$out/work" --force --output "$out/physical.json" > "$out/synth.log" 2>&1

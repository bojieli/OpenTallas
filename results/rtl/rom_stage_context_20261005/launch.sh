#!/bin/bash
set -euo pipefail
: "${WT:?own pinned source}" "${JOB:?NVMe run root}"
cd "$WT"
python3 - <<'PY'
import hashlib,json
from pathlib import Path
p=json.loads(Path('results/rtl/rom_stage_context_20261005/source_pins.json').read_text())
for f,h in p.items():
 assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,'changed source: '+f
PY
mkdir -p "$JOB"
args=()
while read -r src;do args+=(--source "$src");done < results/rtl/rom_stage_context_20261005/sources.txt
export OT_ORFS_NUM_CORES=20
exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record "$JOB/macro_gate.json" \
 --persistent-workdir "$JOB/work" --launch-receipt "$JOB/receipt.json" --view asap7 --top ot_w5_context "${args[@]}" \
 --param ENABLE=1 --clock-period-ns 0.8333333333333333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --io-delay-fraction 0.2 --stages pnr --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --die-area 0 0 1040.256 239.76 --core-area 0 0.27 1040.256 239.49 --place-density 0.55 --macro-place-halo 2 2 \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.01 --hold-corners WC,BC --orfs-corner WC \
 --step-tcl POST_MACRO_PLACE=physical/w5_context/place.tcl --step-tcl POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl --orfs-var ROUTING_LAYER_ADJUSTMENT=0.22 \
 --sdc-append physical/w5_context/context_clocks.sdc \
 --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
 --nickname-tag w5_context_r1_20261005 --output "$JOB/out" --pnr-stop-after finish

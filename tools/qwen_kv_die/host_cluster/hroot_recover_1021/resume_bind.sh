#!/usr/bin/env bash
set -euo pipefail
cd controller_onebank
cp ../integrated_bind.py .
L='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
python3 integrated_bind.py --parent ../partition_onebank/partitioned.json --abi scalar_abi.json --projection projection.json --plan external_outputs.json --generation qkd_hr_ingest_soft_n32.json --native native.json --out parent_bound.json --record reconnection.json > reconnect.log
# actual assembled source, not an isolated cut, goes through independent census.
yosys -l whole.log -p "$L read_json parent_bound.json; read_verilog qkd_hr_ingest_soft_n32.sv; hierarchy -check -top qkd_hr_ingest_qm; write_verilog -noattr whole_integrated.v; stat" > whole_stdout.log 2>&1
args=(python3 native_census.py --netlist whole_integrated.v --top qkd_hr_ingest_qm --out whole_native.json);for f in libs/*.lib macro_libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > whole_native.log 2>&1

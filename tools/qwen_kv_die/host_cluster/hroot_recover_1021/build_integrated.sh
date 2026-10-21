#!/usr/bin/env bash
set -euo pipefail
mkdir -p controller_integrated
cd controller_integrated
for f in extract_soft.py project_unused_cut.py normalize_cut_ports.py engine_native32.py engine_copy_certificate.py bind_copy_inputs.py textbook_lint.py native_census.py macro_bb.v integrated_bind.py generate_integrated.py;do cp ../"$f" .;done
ln -sfn ../libs libs;ln -sfn ../macro_libs macro_libs
python3 extract_soft.py ../partition_integrated/partitioned.v full_cut.v > extraction.json
python3 project_unused_cut.py --json ../partition_integrated/partitioned.json --source full_cut.v --out projected_cut.v --record projection.json > projection.log
python3 normalize_cut_ports.py --source projected_cut.v --parser textbook_lint.py --out original.v --record scalar_abi.json > scalar_abi.log
python3 integrated_bind.py --parent ../partition_integrated/partitioned.json --abi scalar_abi.json --projection projection.json --plan external_outputs.json > output_plan.log
python3 generate_integrated.py > generate.log
python3 bind_copy_inputs.py --source qkd_hr_ingest_soft_n32.sv --record qkd_hr_ingest_soft_n32.json --out bound_inputs.v
python3 engine_copy_certificate.py --original original.v --mapped bound_inputs.v --parser textbook_lint.py --record qkd_hr_ingest_soft_n32.json --out correspondence.json > correspondence.log
L='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l resynth.log -p "$L read_verilog -lib macro_bb.v; read_verilog qkd_hr_ingest_soft_n32.sv; hierarchy -check -top qkd_hr_ingest_soft_n32; synth -top qkd_hr_ingest_soft_n32 -noabc; write_verilog -noattr resynth.v" > resynth_stdout.log 2>&1
args=(python3 native_census.py --netlist resynth.v --top qkd_hr_ingest_soft_n32 --out native.json);for f in libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > native.log 2>&1
python3 integrated_bind.py --parent ../partition_integrated/partitioned.json --abi scalar_abi.json --projection projection.json --plan external_outputs.json --generation qkd_hr_ingest_soft_n32.json --native native.json --out parent_bound.json --record reconnection.json > reconnect.log
# actual assembled source, not an isolated cut, goes through independent census.
yosys -l whole.log -p "$L read_verilog -lib macro_bb.v; read_json parent_bound.json; read_verilog qkd_hr_ingest_soft_n32.sv; hierarchy -check -top qkd_hr_ingest_qm; write_verilog -noattr whole_integrated.v; stat" > whole_stdout.log 2>&1
args=(python3 native_census.py --netlist whole_integrated.v --top qkd_hr_ingest_qm --out whole_native.json);for f in libs/*.lib macro_libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > whole_native.log 2>&1

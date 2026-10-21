#!/usr/bin/env bash
set -euo pipefail
mkdir -p soft_copy_probe
cd soft_copy_probe
cp ../partition_probe_r2/partitioned.v .
for f in engine_native32.py engine_copy_certificate.py bind_copy_inputs.py textbook_lint.py extract_soft.py native_census.py macro_bb.v;do cp ../"$f" .;done
ln -sfn ../libs libs
python3 extract_soft.py partitioned.v original.v > extraction.json
SOURCE_SHA=$(sha256sum original.v | cut -d' ' -f1)
python3 engine_native32.py --netlist original.v --parser textbook_lint.py --sha256 "$SOURCE_SHA" --top qkd_hr_ingest_soft_n32 --out qkd_hr_ingest_soft_n32.sv > generate.log
python3 bind_copy_inputs.py --source qkd_hr_ingest_soft_n32.sv --record qkd_hr_ingest_soft_n32.json --out bound_inputs.v
python3 engine_copy_certificate.py --original original.v --mapped bound_inputs.v --parser textbook_lint.py --record qkd_hr_ingest_soft_n32.json --out correspondence.json > correspondence.log
L='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l resynth.log -p "$L read_verilog -lib macro_bb.v; read_verilog qkd_hr_ingest_soft_n32.sv; hierarchy -check -top qkd_hr_ingest_soft_n32; synth -top qkd_hr_ingest_soft_n32 -noabc; write_verilog -noattr resynth.v" > resynth_stdout.log 2>&1
args=(python3 native_census.py --netlist resynth.v --top qkd_hr_ingest_soft_n32 --out native.json);for f in libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > native.log 2>&1

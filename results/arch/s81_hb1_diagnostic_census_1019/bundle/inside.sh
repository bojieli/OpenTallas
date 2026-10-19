#!/bin/bash
set -euo pipefail
python3 /src/preflight.py
source /OpenROAD-flow-scripts/env.sh
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/src/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/results/asap7/s81_hb1_diagnostic_1019/base/1_2_yosys.v > /work/synth.log 2>&1
cp /work/results/asap7/s81_hb1_diagnostic_1019/base/1_2_yosys.v /work/raw.v
python3 - <<'ENDPY'
import pathlib,re,json
p=pathlib.Path('/work/raw.v');s=p.read_text();s,n=re.subn(r'\b(input|output|wire|reg)\s+signed\b',r'\1',s);pathlib.Path('/work/normalized.v').write_text(s);json.dump({'signed_declarations_removed':n},open('/work/normalization.json','w'))
ENDPY
/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -p 'read_verilog /work/raw.v; write_json /work/mapped.json' > /work/mapped_json.log 2>&1
/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/link.tcl > /work/link.log 2>&1
/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/odb_census.py /work/unplaced.odb /work/native_census.json.gz /work/native_summary.json > /work/census.log 2>&1

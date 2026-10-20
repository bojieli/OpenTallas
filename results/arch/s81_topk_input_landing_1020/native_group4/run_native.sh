#!/bin/bash
set -euo pipefail
S=$PWD
mkdir -p native3
sha256sum dut_hq_in.sv config.mk clock.sdc physical/common_flow/ot* tools/textbook_lint.py tools/ref_tile/native_census.py > native3/inputs.sha256
docker run --rm -v "$S:/src:ro" -v "$S/native3:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/src/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > native3/synth.log 2>&1
docker run --rm -v "$S:/src:ro" -v "$S/native3:/work" openroad/orfs:asap7lock bash -lc 'set -eu; a=(); for p in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*; do a+=(--liberty "$p"); done; python3 /src/tools/ref_tile/native_census.py --netlist /work/results/asap7/codex_hq_input_raw/base/1_2_yosys.v --top ot_s81ph_hq_in "${a[@]}" --out /work/native.json' > native3/native.log 2>&1
docker run --rm -v "$S:/src:ro" -v "$S/native3:/work" openroad/orfs:asap7lock python3 /src/tools/textbook_lint.py check --netlist /work/results/asap7/codex_hq_input_raw/base/1_2_yosys.v --top ot_s81ph_hq_in --out /work/textbook.json > native3/textbook.log 2>&1
python3 - <<'PYC' 
import json
p=json.load(open('native3/native.json'));print('INPUT_RAW_NATIVE',p['status'],'max',p['max_dynamic_loads'],'violations',len(p['violations']),'roles',len(p['role_errors']))
PYC

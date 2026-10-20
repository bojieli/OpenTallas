#!/bin/bash
set -euo pipefail
S=$PWD
mkdir -p native2
sha256sum dut_hq_in.sv config.mk clock.sdc physical/common_flow/*.tcl tools/textbook_lint.py tools/ref_tile/native_census.py > native2/inputs.sha256
docker run --rm -v "$S:/src:ro" -v "$S/native2:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/src/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > native2/synth.log 2>&1
docker run --rm -v "$S:/src:ro" -v "$S/native2:/work" openroad/orfs:asap7lock bash -lc 'set -eu; a=(); for p in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*; do a+=(--liberty "$p"); done; python3 /src/tools/ref_tile/native_census.py --netlist /work/results/asap7/codex_hq_input_raw/base/1_2_yosys.v --top ot_s81ph_hq_in "${a[@]}" --out /work/native.json' > native2/native.log 2>&1
python3 - <<'PYC'
import json
p=json.load(open('native2/native.json'));print('INPUT_RAW_NATIVE',p['status'],'max',p['max_dynamic_loads'],'violations',len(p['violations']),'roles',len(p['role_errors']))
PYC

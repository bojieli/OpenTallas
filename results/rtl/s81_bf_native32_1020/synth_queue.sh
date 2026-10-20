#!/bin/bash
set -eu
python3 - <<'PYCFG'
from pathlib import Path
p=Path('work/config.mk');s=p.read_text().replace('export VERILOG_DEFINES = -DOT_BF_FOREP32','export VERILOG_DEFINES = -DOT_BF_QUEUE32 -DOT_BF_FOREP32');p.write_text(s)
PYCFG
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 synth"

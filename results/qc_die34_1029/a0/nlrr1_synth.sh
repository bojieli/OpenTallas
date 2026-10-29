#!/bin/bash
set -euo pipefail
k=/srv/opentallas-scratch2/claude/die-qc34-a0/kits/qfd_tile_nl_a0c_a0nl14icg2rr1
sudo docker run --rm --name dqc34-a0-nlrr1-synth --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 synth
" > "$k/synth.log" 2>&1

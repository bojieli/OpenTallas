#!/bin/bash
# PATH-QC-N59-5 fresh LEC of the combined netlist (fix 2 + fix 3), kit lec.py (released flow 1d335f9d99) on 1_2_yosys.v
set -uo pipefail
K=/srv/opentallas-scratch2/claude/path-qc-n59-5/gen/native59
cmp /srv/opentallas-scratch2/claude/wt/path-qc-n59-4-1025/tools/die_plan/lec.py $K/lec.py.n59_deferred || exit 9
docker run --rm --name pathqc-n59-5-lec --memory=64g --memory-swap=64g --cpus=8 -v $K:/work -v /srv/opentallas-scratch2/claude/wt/path-qc-n59-4-1025:/repo:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /repo/tools/die_plan/lec.py /work --netlist /work/run/results/asap7/dp_native59/base/1_2_yosys.v --out /work/lec --jobs 8 > /work/lec_run.log 2>&1; echo LEC_EXIT \$?; tail -2 /work/lec_run.log"

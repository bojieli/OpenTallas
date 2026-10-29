#!/bin/bash
set -euo pipefail
kind=$1
p=/srv/opentallas-scratch2/claude/codex-head-kits-0822/lec_seed/$kind
docker run --rm --name codex-head-seedlec-$kind --cpus=8 -v "$p:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/lec.py /work --netlist /work/synth.v --out /work/lec' > "$p/seedlec.log" 2>&1

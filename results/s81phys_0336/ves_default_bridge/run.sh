#!/bin/bash
set -euo pipefail
K=$1
docker run --rm --name "codex-ves-defaultbridge-$$" --cpus 2 --memory 4g --memory-swap 4g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for t in old current mutant; do yosys -Q -T -s /work/$t.ys > /work/$t.yosys.log 2>&1; done'

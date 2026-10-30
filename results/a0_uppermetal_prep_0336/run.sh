#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-qc-a0-0336
for kind in nk nl; do
 sudo docker run --rm --name "codex-a0-${kind}-uppermetal-0336" --cpus=1 --memory=8g --memory-swap=8g -v "$B/uppermetal":/work -v "$B/uppermetal/$kind":/out -v "$B/physical/${kind}_pin_clock_install":/odb:ro -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/dump_upper.tcl > /out/dump.log 2>&1'
done

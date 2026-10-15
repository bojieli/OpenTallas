#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch/codex/flow-prects-1103/proof
OLD=/srv/opentallas-scratch/claude/ref_gate/qfd_slab_pair_add-20261015-103006
SRC=/srv/opentallas-scratch/codex/flow-prects-1103/src
for CASE in saved_pre fixed_saved_pre; do
 docker run --rm -v "$OLD/src:/src:ro" -v "$OLD/routes/gate/work/orfs:/work:ro" -v "$P:/proof" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/proof/$CASE.tcl" > "$P/$CASE.log" 2>&1
 python3 "$SRC/tools/preroute_gate.py" check "$P/$CASE.json" --out "$P/$CASE.judgement.json" > "$P/$CASE.judgement.log" || test "$CASE" = saved_pre
done

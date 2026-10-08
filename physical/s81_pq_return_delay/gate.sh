#!/bin/bash
set -euo pipefail
W=${1:?new gate output path}
[ ! -e "$W" ] || { echo 'Preserving existing gate output'; exit 1; }
mkdir -p "$W"
IMG=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm -v "$PWD:/src:ro" -v "$W:/p" "$IMG" bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/physical/s81_pq_return_delay/fixture/check.tcl' > "$W/gate.log" 2>&1
grep -q 'PQ_DELAY_TOPOLOGY_PASS endpoints=2 cells=6 placement_checked=1' "$W/gate.log"
grep -q 'PQ_DELAY_SWAP_MUTANT_REJECTED' "$W/gate.log"
grep -q 'PQ_DELAY_DROP_MUTANT_REJECTED' "$W/gate.log"
grep -q 'PQ_DELAY_MECHANISM_GATE_PASS' "$W/gate.log"
echo 'PQ_DELAY_MECHANISM_GATE_PASS endpoints=2 cells=6 negative_controls=2'

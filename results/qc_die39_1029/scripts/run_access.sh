#!/bin/bash
# DIE-QC-39: provider clock access for the leaf-driver ODB: loads = 3,266 trunk-side inverter A pins,
# retained clock = R7 re-sited clock-cell stacks (from prov_R7D prebuild shapes) instead of the pre-resite clock_seed.
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=$Q/codex-qc-provider-clock-0834; I=$Q/codex-qc-import-0824; O=$Q/die-qc39/$1; mkdir -p $O
docker run --rm --name dqc39-access-$$ --memory=64g --memory-swap=64g --cpus=8 -v "$Q:$Q" -e PYTHONPATH="$I/pydeps" -w $Q/die-qc39/src_pc/tools/clk python:3.12 python plan_provider_clock_access_leaf.py --geometry $Q/die-qc39/leaf_geom/geometry.json --loads $Q/die-qc39/leaf_loads.json --graph "$R/corrected/graph.json" --via-facts "$Q/codex-qc-mesh5-1029/census119_h800/probe_census.json" --retained-clock $2 --reserved-power "$I/reachfix/pg_candidate/reserved_access.json" --out $O > $O/plan_access.log 2>&1 || echo "rc $?" >> $O/plan_access.log
chown -R 1000:1000 $O 2>/dev/null || true

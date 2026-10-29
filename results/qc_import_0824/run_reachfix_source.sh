#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-import-0824
F=$R/reachfix
W=$Q/wt/codex-qc-import-0824
O=$Q/qc-import-1
B=$Q/codex-qc-1029/baseline26
mkdir -p "$F/islands"
docker run --rm --name codex-qci-reachfix-target-$$ --memory=40g --memory-swap=40g --cpus=4 -v "$Q:$Q" -w "$R" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $F' EXIT; pip -q install jsonschema shapely pyyaml numpy >/dev/null 2>&1; python $R/src/provider_sites.py $W/tools/die_plan $O/plan/plan_qc_import1.json $F/placements.json $B/islands119_h800/clock_island_sites.json $F/islands > $F/islands.log; python $R/src/fresh_target.py --plan $O/plan/plan_qc_import1.json --base $B/target119_h800 --sites $B/islands119_h800/clock_island_sites.json $F/islands/provider_sites.json --tools $W/tools/die_plan --out $F/target > $F/target.log 2>&1"
mkdir -p "$F/mechanics"
for f in prepare_clock.tcl prepare_signal.tcl obs_pg.tcl clkonly.v inside.sh graft.py; do cp "$O/mechanics/$f" "$F/mechanics/"; done
docker run --rm --name codex-qci-reachfix-mech-$$ --memory=48g --memory-swap=48g --cpus=8 -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -e CORNER=TT -v "$F/target:/work:ro" -v "$F/mechanics:/out" -v "$F/mechanics/graft.py:/graft.py:ro" openroad/orfs:asap7lock bash /out/inside.sh
tail -3 "$F/mechanics/graft.log"

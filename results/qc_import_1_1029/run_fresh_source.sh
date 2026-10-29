#!/bin/bash
# QC-IMPORT-1 fresh native source: (1) static target with combined islands + reset infra, (2) prepare clock/signal
# ODBs + graft the frozen trial26 clock onto the actual partition clock ITerms (same recipe as mechanics119_h800).
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/qc-import-1
WT=$Q/wt/qc-import-1
B=$Q/codex-qc-1029/baseline26
T=$R/target
M=$R/mechanics
echo "START $(date)"
docker run --rm --name qcimp1-target-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R python:3.12 bash -c "
pip -q install jsonschema shapely pyyaml numpy >/dev/null 2>&1
python fresh_target.py --plan $R/plan/plan_qc_import1.json --base $B/target119_h800 \
  --sites $B/islands119_h800/clock_island_sites.json $R/islands/provider_sites.json --tools $WT/tools/die_plan --out $T
chown -R $(id -u):$(id -g) $T"
echo "TARGET_DONE $(date)"
mkdir -p $M
for f in prepare_clock.tcl prepare_signal.tcl obs_pg.tcl clkonly.v inside.sh; do cp $B/mechanics119_h800/$f $M/; done
cp $Q/codex-qc-1029/graft_clock_targets6.py $M/graft.py
sha256sum $M/* > $M/inputs.sha256
docker run --rm --name qcimp1-mech-$$ --memory=48g --memory-swap=48g --cpus=8 \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -e CORNER=TT \
  -v $T:/work:ro -v $M:/out -v $M/graft.py:/graft.py:ro openroad/orfs:asap7lock bash /out/inside.sh
echo "MECH_DONE $(date)"
tail -3 $M/graft.log

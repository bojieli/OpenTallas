#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=/srv/opentallas-scratch2/claude/die-qc34; O=$R/gridvias
mkdir -p $O
docker run --rm --name dqc34-gridvias-$$ --memory=64g --memory-swap=64g --cpus=2 -v "$Q:$Q" -w "$R" openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $O\" EXIT; openroad -python -exit $R/src/grid_vias.py $R/fullpg_mat/provider_pg.odb $O $R/reachfix/readback/pg_rects.json > $O/run.log 2>&1"
tail -30 $O/run.log

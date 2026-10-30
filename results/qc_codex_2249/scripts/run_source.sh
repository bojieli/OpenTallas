#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
I=$Q/codex-qc-import-0824
mkdir -p "$R/source" "$R/readback"
cp "$I/reachfix/mechanics/endpoints.json" "$R/readback/"
cp "$Q/die-qc41/prov_R7BFR3/pg_rects.json" "$R/readback/"
cp "$Q/die-qc36/readback_resite/probe_census.json" "$R/readback/"
docker run --rm --name codexqc2249-source-$$ --memory=64g --memory-swap=64g --cpus=4 -v "$Q:$Q" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $R/source $R/readback' EXIT; openroad -python -exit $R/src/prepare_source.py --source $Q/die-qc38/leaf_apply/provider/provider.odb --tree $Q/die-qc36/resite/tree_resite.json --out $R/source > $R/source/prepare.log 2>&1; openroad -python -exit $I/src/export_geometry119.py --odb $R/source/provider.odb --out $R/readback > $R/readback/export.log 2>&1; openroad -python -exit $R/src/readback_current.py --odb $R/source/provider.odb --cells $Q/die-qc38/leaf_apply/provider/all_cells.json --out $R/readback > $R/readback/reach.log 2>&1"

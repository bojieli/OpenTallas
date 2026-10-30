#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-import-0824; F=$R/reachfix; W=$Q/wt/codex-qc-import-0824
L=$Q/die-qc37/leaf_fixed_rf; O=$Q/die-qc38/leaf_apply
docker run --rm --name dqc38-leafapply-$$ --memory=40g --memory-swap=40g --cpus=4 -v "$Q:$Q" -w "$O" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $O\" EXIT; openroad -python -exit $W/results/qc_import_3_1029/apply_cells.py --source $F/bound/source_bound.odb --inventory $L/provider_cells_leaf.json --mapped $L/provider_mapped_leaf.json --placements $L/placements_leaf.json --bindings $F/bound/bindings.json --preflight $L/preflight/preflight.json --review $O/review_record.json --out $O/provider > $O/provider/apply.log 2>&1; openroad -python -exit $R/src/readback_complete.py --odb $O/provider/provider.odb --cells $O/provider/all_cells.json --out $O/readback > $O/readback/reach.log 2>&1"
cat $O/readback/summary.json

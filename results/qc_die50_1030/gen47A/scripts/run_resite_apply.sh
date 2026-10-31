#!/bin/bash
# DIE-QC-50/gen47A step 1b: move the 2,581 re-sited clock cells in the leaf-import ODB (Codex 2249 prepare_source.py, copy)
# then re-export + leaf A-pin loads + lower access on the re-sited ODB (run_access_leaf.sh with SRC override)
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; A=$Q/die-qc-50/gen47A; M=$Q/wt/die-qc-50-gen47A/results/qc_die50_1030/gen47A/scripts
mkdir -p $A/source
docker run --rm --name dqc50g47A-src-$$ --memory=32g --memory-swap=32g --cpus=2 -v $Q:$Q openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $A/source' EXIT; openroad -python -exit $M/prepare_source47.py --source $A/import/provider.odb --tree $A/resite/tree47_resite.json --out $A/source > $A/source/prepare.log 2>&1"
tail -1 $A/source/prepare.log
bash $M/run_access_leaf.sh $A/source/provider.odb $A/access_rs

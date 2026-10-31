#!/bin/bash
# DIE-QC-50/gen47A step 0b: preflight (gen47b preflight.py) + Codex apply_cells of the leaf-augmented provider on gen47b source_bound.odb
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; A=$Q/die-qc-50/gen47A; B=$Q/die-qc-50/gen47b; G=$Q/die-qc-50/gen47; S=$G/pimp_src
W=$Q/wt/die-qc-50-gen47A; P=$W/results/qc_die50_1030/gen47b/scripts
INV=$A/leaf/provider_cells_leaf.json; MAP=$A/leaf/provider_mapped_leaf.json; PLC=$A/leaf/placements_leaf.json; PL=$B/inputs/plan_qc49.json
mkdir -p $A/import
STEP=${1:-pre}
if [ $STEP = pre ]; then
docker run --rm --name dqc50g47A-pre-$$ --memory=32g --memory-swap=32g --cpus=4 -v $Q:$Q -w $A python:3.12 bash -c "
pip -q install shapely >/dev/null 2>&1
python $P/preflight.py --inventory $INV --mapped $MAP --placements $PLC \
  --proposal-constraints $G/pimp/constraints/constraints.json --fresh-constraints $B/bound/constraints/constraints.json \
  --bindings $B/bound/bindings.json --die-plan $PL --out $A/import/preflight.json > $A/import/preflight.log 2>&1; chown -R 1000:1000 $A/import; true"
python3 -c "import json;d=json.load(open('$A/import/preflight.json'));print(d['verdict'],json.dumps(d['issues']),json.dumps(d.get('samples',[])[:5])[:1500])"
else
docker run --rm --name dqc50g47A-apply-$$ --memory=64g --memory-swap=64g --cpus=4 -v $Q:$Q -w $A openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $A/import' EXIT
openroad -python -exit $S/apply_cells.py --source $B/bound/source_bound.odb --inventory $INV --mapped $MAP --placements $PLC \
  --bindings $B/bound/bindings.json --preflight $A/import/preflight.json --review $A/import/review_record.json --out $A/import > $A/import/apply.log 2>&1"
tail -20 $A/import/apply.log
fi

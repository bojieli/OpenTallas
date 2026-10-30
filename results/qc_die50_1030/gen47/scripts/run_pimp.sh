#!/bin/bash
# DIE-QC-50/gen47 (a) provider placement PROPOSAL on the gen47 source (Codex provider-import-1029 scripts, copied read-only; new inputs)
# export_constraints -> make_budget (Codex wave2 policy 18x4.32 / root 32x8.64) -> plan_place -> reach -> islands -> stage_boxes
set -u
Q=/srv/opentallas-scratch2/claude; D=$Q/die-qc-50/gen47; W=$Q/wt/die-qc-50-gen47; S=$D/pimp_src; O=$D/pimp; mkdir -p $O
cat > $O/inner.sh <<IN
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'chown -R 1000:1000 $O' EXIT
cd $O
SRC=$Q/die-qc-49/g47src/build2/clock_native.odb; INV=$D/synthP/provider_cells.json; PL=$W/physical/die_plan/qwen_compute/plan_of_record/plan_qc49.json; T=$W/tools/die_plan
openroad -python -exit $S/export_constraints.py --source \$SRC --inventory \$INV --die-plan \$PL --tools \$T --out $O/constraints > $O/export.log 2>&1; echo EXPORT_OK
python3 $S/make_budget.py --inventory \$INV --width 18 --height 4.32 --root-width 32 --root-height 8.64 --root-if-cells 31 --center legacy-ff --site-pitch 0.054 --row-pitch 0.54 --row-origin-x 0 --row-origin-y 0 --policy-owner DIE-QC-50-gen47-diagnostic-Codex-wave2-policy --out $O/budget.json > $O/budget.log 2>&1; echo BUDGET_OK
python3 $S/plan_place.py --inventory \$INV --constraints $O/constraints/constraints.json --budget $O/budget.json --out $O/proposal > $O/place.log 2>&1; echo PLACE_OK
python3 $S/reach.py --inventory \$INV --placements $O/proposal/placements.json --constraints $O/constraints/constraints.json --out $O/proposal/reach.json > $O/reach.log 2>&1; echo REACH_OK
openroad -python -exit $S/emit_islands.py --placements $O/proposal/placements.json --die-plan \$PL --tools \$T --out $O/proposal/islands > $O/islands.log 2>&1; echo ISL_OK
python3 $S/stage_boxes.py --inventory \$INV --placements $O/proposal/placements.json --constraints $O/constraints/constraints.json --reach $O/proposal/reach.json --out $O/proposal/stage_boxes.json > $O/boxes.log 2>&1; echo BOX_OK
IN
docker run --rm --name dqc50-g47-pimp-$$ --memory=64g --memory-swap=64g --cpus=4 -v $Q:$Q openroad/orfs:asap7lock bash $O/inner.sh > $O/chain.log 2>&1
echo "rc=$? $(date)" > $O/status

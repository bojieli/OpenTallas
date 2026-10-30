#!/bin/bash
# DIE-QC-50/gen47 (a) provider placement proposal, steps after export/budget: plan_place/reach/stage_boxes in python:3.12 (+shapely), islands in orfs
set -u
Q=/srv/opentallas-scratch2/claude; D=$Q/die-qc-50/gen47; W=$Q/wt/die-qc-50-gen47; S=$D/pimp_src; O=$D/pimp
INV=$D/synthP/provider_cells.json; PL=$W/physical/die_plan/qwen_compute/plan_of_record/plan_qc49.json; T=$W/tools/die_plan
rm -f $O/status
docker run --rm --name dqc50-g47-pimp2-$$ --memory=64g --memory-swap=64g --cpus=4 -v $Q:$Q -w $O python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $O' EXIT; pip -q install shapely numpy >/dev/null 2>&1; python $S/plan_place.py --inventory $INV --constraints $O/constraints/constraints.json --budget $O/budget.json --out $O/proposal > $O/place.log 2>&1; echo PLACE_OK; python $S/reach.py --inventory $INV --placements $O/proposal/placements.json --constraints $O/constraints/constraints.json --out $O/proposal/reach.json > $O/reach.log 2>&1; echo REACH_OK; python $S/stage_boxes.py --inventory $INV --placements $O/proposal/placements.json --constraints $O/constraints/constraints.json --reach $O/proposal/reach.json --out $O/proposal/stage_boxes.json > $O/boxes.log 2>&1; echo BOX_OK" >> $O/chain.log 2>&1
rc=$?
[ $rc = 0 ] && docker run --rm --name dqc50-g47-isl-$$ --memory=32g --memory-swap=32g --cpus=2 -v $Q:$Q -w $O openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit $S/emit_islands.py --placements $O/proposal/placements.json --die-plan $PL --tools $T --out $O/proposal/islands > $O/islands.log 2>&1; r=\$?; chown -R 1000:1000 $O; echo ISL_rc=\$r; exit \$r" >> $O/chain.log 2>&1
rc=$?
echo "rc=$rc $(date)" > $O/status

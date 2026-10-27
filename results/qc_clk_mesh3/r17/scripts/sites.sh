#!/bin/bash
# sites.sh NAME extra-args : physical site export + identity (assign_periodic) on the pkg inputs
P=/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg; W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r17-1027; N=$1; shift
mkdir -p $P/out/$N
docker run --rm --name qcr17-sites-$N --memory 24g --cpus 2 -e PYTHONPATH=/w/die_plan -v $P:/w -v $W/tools/die_plan:/w/die_plan:ro -w /w ot-ngspice:r3 sh -c "python3 r17_phys_sites.py --r2 ${R2:-inputs/r2_plan_w.json} --stage inputs/stage_table.json --lanes vss --island-edge-sym $* --out out/$N/sites > out/$N/sites.log 2>&1; chown -R $(id -u):$(id -g) /w/out"

#!/bin/bash
# r14_dry.sh SPEC OUTDIR [extra]: dry explicit-cells build on the QC plan (plan PG grid, default tracks). UNCHECKED
P=/srv/opentallas-scratch2/claude/qc-mesh-r12/pkg; W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r15-1026; S=$1; O=$2; shift 2
docker run --rm --memory 16g --cpus 2 -v $P:/w -v $W/tools/die_plan:/w/die_plan:ro -v $HOME/.cache/opentallas:/root/.cache/opentallas:ro -w /w ot-ngspice:r3 sh -c "python3 die_plan/die_clock_mesh.py build inputs/candidate_oneqc0733.json --explicit-cells $S --ndr 16w --out $O $* > $O.log 2>&1; chown -R $(id -u):$(id -g) /w/out"
head -1 $P/$O.log

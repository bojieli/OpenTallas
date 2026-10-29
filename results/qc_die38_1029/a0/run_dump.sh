#!/bin/bash
# usage: run_dump.sh KITDIR TAG CORNER  (docker on intel2, memory-capped diagnostic probe)
set -euo pipefail
k=$1; tag=$2; C=$3; s=/srv/opentallas-scratch2/claude/dqc38-a0
sdc=$(ls $k/run/results/asap7/*/base/3_place.sdc); sdc=/work/${sdc#$k/}
sudo docker run --rm --name dqc38-$tag-$C --cpus=2 --memory=12g --memory-swap=12g -v "$k":/work:ro -v $s:/out \
  -e ODB=/work/diag/cts_prehold.odb -e OT_CORNER=$C -e OUT=/out/$tag -e PLACE_SDC=$sdc -e SKIP_TREE=${SKIP_TREE:-} -e HOLD_TSV=/work/diag/hold_fail.tsv \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /out/ck_stage_dump.tcl" > $s/${tag}_${C}.log 2>&1

#!/bin/bash
# usage: run_hold_all.sh KITDIR TAG SMAX_PS   (docker on intel2, memory-capped diagnostic probe, read-only kit)
set -euo pipefail
k=$1; tag=$2; S=$3; s=/srv/opentallas-scratch2/claude/dqc39-a0
sdc=$(ls $k/run/results/asap7/*/base/3_place.sdc); sdc=/work/${sdc#$k/}
sudo docker run --rm --name dqc39-hold-$tag --cpus=2 --memory=12g --memory-swap=12g -v "$k":/work:ro -v $s:/out \
  -e ODB=/work/diag/cts_prehold.odb -e PLACE_SDC=$sdc -e SMAX=$S -e OUT=/out/${tag}_hold_all_ff.tsv \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /out/hold_all.tcl" > $s/${tag}_hold_all.log 2>&1

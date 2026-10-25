#!/bin/bash
# stage.sh SRC DST : copy a Codex south4_clock kit up to 3_place (no CTS/GRT products) into a fresh S8BP kit dir
set -eu
SRC=$1; DST=$2; mkdir -p $DST
rsync -a --exclude 'run/results/*/*/base/4_*' --exclude 'run/results/*/*/base/5_*' --exclude 'run/results/*/*/base/route.guide' \
  --exclude 'run/logs/*/*/base/4_*' --exclude 'run/logs/*/*/base/5_*' --exclude 'run/reports' --exclude 'run/objects/*/*/base/*cts*' \
  --exclude clock_probe.log --exclude clock_placed.csv --exclude grt_pair_skew.tsv --exclude CLOCK_PROBE.json $SRC/ $DST/
cp $(dirname $0)/struct_cts.tcl $(dirname $0)/meas.tcl $DST/
echo "{\"source\": \"$SRC\", \"staged\": \"$(date -Is)\", \"lane\": \"QC-S8BP\"}" > $DST/S8BP_STAGE.json
ls $DST/run/results/asap7/*/base/

#!/bin/bash
set -euo pipefail
k=$1; tag=$2; s=/srv/opentallas-scratch2/claude/dqc38-a0
sudo docker run --rm --name dqc38-pairs-$tag --cpus=2 --memory=8g --memory-swap=8g -v "$k":/work:ro -v $s:/out \
  -e ODB=/work/diag/cts_prehold.odb -e OUT=/out/${tag}_zl_pairs.tsv openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /out/zl_pairs.tcl" > $s/${tag}_pairs.log 2>&1

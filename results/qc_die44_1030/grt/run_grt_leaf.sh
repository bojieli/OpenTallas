#!/bin/bash
# DIE-QC-44: usage run_grt_leaf.sh NAME CLKLAYERS CORNER
set -u
N=$1; L=$2; C=$3; Q=/srv/opentallas-scratch2/claude; O=$Q/die-qc-44/grt/$N; mkdir -p $O
docker run --rm --name dieqc44-grt-$N-$$ --memory=128g --memory-swap=128g --cpus=16 -v $Q:/s -e OUT=/s/die-qc-44/grt/$N -e CLKLAYERS=$L -e CORNER=$C openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -exit /s/die-qc-44/grt/grt_leaf.tcl > /s/die-qc-44/grt/$N/run.log 2>&1; rc=\$?; openroad -python -exit /s/die-qc-44/leaf/leaf_layers.py /s/die-qc-44/grt/$N/routed.odb /s/die-qc-44/grt/$N/leaf_layers.json > /s/die-qc-44/grt/$N/leaf.log 2>&1; chown -R 1000:1000 /s/die-qc-44/grt/$N; exit \$rc"
echo "rc=$? $(date)" > $O/status

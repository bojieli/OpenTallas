#!/bin/bash
# DIE-QC-45: usage run_edge.sh CORNER   (diagnostic probe, docker with memory cap, epyc2)
set -u
C=$1; Q=/srv/opentallas-scratch2/claude; O=$Q/die-qc-45/sta/E$C; mkdir -p $O
docker run --rm --name dieqc45-edge-$C-$$ --memory=128g --memory-swap=128g --cpus=16 -v $Q:/s -e OUT=/s/die-qc-45/sta/E$C -e CORNER=$C openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -exit /s/die-qc-45/sta/edge_readout.tcl > /s/die-qc-45/sta/E$C/run.log 2>&1; rc=\$?; chown -R 1000:1000 /s/die-qc-45/sta/E$C; exit \$rc"
echo "rc=$? $(date)" > $O/status

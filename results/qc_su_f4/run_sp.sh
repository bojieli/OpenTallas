#!/bin/bash
# QC-SU-F4 diagnostic: ORFS synth + place only (no sdc_lint/face_guard gates; plan-geometry probe, not a kit)
K=$1; docker run --rm --name f4sp-$(basename $K)-$$ --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8\"; \$M synth && \$M place; rc=\$?; P=\$(ls /work/run/results/asap7/*/base/3_place.odb | tail -1); ODB=\$P OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py > /work/dump_placed.log 2>&1; chown -R \$HUID:\$HGID /work; exit \$rc" > $K/run_sp.log 2>&1
echo "rc $? $(date -Is)" >> $K/run_sp.log

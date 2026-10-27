#!/bin/bash
# HBM-CORE-LAT-R4: place only (no CTS) + placed.csv dump; KITDIR
K=$(cd "$1" && pwd -P); N=hcr4pl-$(basename $K | cut -c1-40)-$$
docker run --rm --name $N --cpus=8 --memory=8g --memory-swap=8g -v $K:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place > /work/place_r4.log 2>&1; rc=\$?; R=\$(ls -d /work/run/results/asap7/*/base); if [ -f \$R/3_place.odb ]; then ODB=\$R/3_place.odb OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py > /work/dump_placed.log 2>&1; fi; chown -R $(id -u):$(id -g) /work; exit \$rc"

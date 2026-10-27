#!/bin/bash
# run_solve.sh PKG NAME CORNER SAMPLE "extra args"  (one capped container)
PKG=$1; NAME=$2; C=$3; S=$4; shift 4
docker run --rm --name qcmesh3-solve-$NAME-$C-$S --memory 12g --cpus 2 -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -v $PKG:/w -w /w ot-ngspice:r3 \
  sh -c "python3 die_plan/qc_clk_mesh3.py solve --r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --thev inputs/thev_r2.json --slew-sens inputs/slew_sens.json --corner $C --sample $S $* --out out/$NAME/${C}_s$(printf %03d $S).json > out/$NAME/${C}_s$(printf %03d $S).log 2>&1; chown -R $(id -u):$(id -g) /w/out"

#!/bin/bash
# run_solve.sh PKG WT NAME CORNER SAMPLE "extra args"  (one capped container; r10: --geometry legal default)
PKG=$1; WT=$2; NAME=$3; C=$4; S=$5; shift 5
mkdir -p $PKG/out/$NAME
F=$(printf %s_s%03d $C $S)
docker run --rm --name qcr10-$NAME-$C-$S --memory 12g --cpus 2 -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 \
  -v $PKG:/w -v $WT/tools/die_plan:/w/die_plan:ro -v $WT/results/qc_clk_mesh3/r10_inputs:/w/r10_inputs:ro -w /w ot-ngspice:r3 \
  sh -c "python3 die_plan/qc_clk_mesh3.py solve --r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --thev inputs/thev_r2.json --slew-sens inputs/slew_sens.json --no-spine --top-w 16w --top-m 2 --top-reach 450 --r9-dir r10_inputs --corner $C --sample $S $* --out out/$NAME/$F.json > out/$NAME/$F.log 2>&1; chown -R $(id -u):$(id -g) /w/out"

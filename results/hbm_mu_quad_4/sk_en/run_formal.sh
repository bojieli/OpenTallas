#!/bin/bash
# HBM-MU-QUAD-4 10-27: run the sk_en reduced LEC / hold / census yosys scripts in docker (memory-capped), from repo root.
set -u
W=$(pwd); F=results/hbm_mu_quad_4/sk_en
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
for s in lec_en1_step0 lec_en1_steady hold_en0_step0 hold_en0_steady stat_step0 stat_steady; do
  docker run --rm --memory=24g --user $(id -u):$(id -g) -v $W:$W -w $W openroad/orfs:asap7lock \
    timeout 3000 $Y -q -l $F/formal/$s.log $F/$s.ys >/dev/null 2>&1; echo "$s rc=$?" | tee -a $F/formal/rc.txt &
done
wait

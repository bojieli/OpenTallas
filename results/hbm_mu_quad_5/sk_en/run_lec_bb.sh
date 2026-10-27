#!/bin/bash
# HBM-MU-QUAD-5: run the 4 blackboxed LEC/hold scripts in parallel (docker, memory-capped), from repo root.
W=$(pwd); F=results/hbm_mu_quad_5/sk_en; Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys; : > $F/formal/rc.txt
for s in lec_bb_step0 lec_bb_steady hold_bb_step0 hold_bb_steady; do
  ( docker run --rm --memory=16g --user $(id -u):$(id -g) -v $W:$W -w $W openroad/orfs:asap7lock \
      timeout 1500 $Y -q -l $F/formal/$s.log $F/$s.ys >/dev/null 2>&1; echo "$s rc=$?" >> $F/formal/rc.txt ) &
done
wait

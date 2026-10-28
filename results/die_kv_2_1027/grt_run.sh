#!/bin/bash
# DIE-KV-2: combo die GRT (die_trial signal kit M4-M7 + link_fishbone clock M8-M9, rep 250) TT+FF, 50 it, -critical_nets_percentage 0
# usage: grt_run.sh TAG KITDIR   (recipe = LAND-KV-2 grtG2.sh + mk_combo_kv.py, ADJ 0.75 / ADJ7 0)
set -e
E=/srv/opentallas-scratch2/claude/die-kv-2-1027; T=$1; K=$2
mkdir -p $E/clk$T; cp $K/clock/ctree.v $K/clock/tree.json $E/clk$T/; cp $K/clock/ctree.tcl $E/clk$T/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $E/out${T}_$C
  CORNER=$C ADJ=0.75 ADJ7=0 python3 /srv/opentallas-scratch2/claude/land-kv-1027/mk_combo_kv.py $K $E/clk$T $E/out${T}_$C
  sed -i "s#/out/#/out/#g" $E/out${T}_$C/combo.tcl
  docker run -d --name dkv2-grt-$T-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $E/out${T}_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
done

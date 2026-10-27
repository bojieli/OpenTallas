#!/bin/bash
# PATH-S81-PD: recompose the FALLBACK-S81-2 G=2 tap table on the UNCHANGED S81 plan with the thin-bank band search
# (no outline/lattice change), regenerate latency, G0. Confirms how many of the 60 band FAILs remain.
set -eu
WT=/srv/opentallas-scratch2/claude/wt/path-s81-pd-1026; O=/srv/opentallas-scratch2/claude/path-s81-pd-1026
SRC=/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81
PD=$O/plandir; mkdir -p $PD; for d in $SRC/*; do b=$(basename $d); case $b in die_plan*.json) ;; *) ln -sfn $d $PD/$b;; esac; done
cd $WT; echo START $(date) code $(git rev-parse --short HEAD)
J=$PD/die_plan_pd_thin.json
python3 results/fallback_s81_1026/compose_plan.py $SRC/die_plan_phyfit_g0fix.json results/fallback_s81_2_1026/regions/class_g2_tap/landed_crossings.json $J $O/side_pd_thin.json > $O/compose_thin.log 2>&1
tail -n 1 $O/compose_thin.log
python3 tools/die_plan/gen.py latency $J --inplace --out $O/gen_lat_thin > $O/gen_lat_thin.log 2>&1
python3 tools/die_plan/check.py $J --out $O/g0_thin > $O/g0_thin.log 2>&1 || true; tail -n 1 $O/g0_thin.log
echo DONE $(date)

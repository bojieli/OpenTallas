#!/bin/bash
# DIE-QC-4 kit (QC-SMALLREG Ggrp recipe: stock link_htree, leaf 200, rep 250, site legal+slide) + clock placement run.
# usage: runKit.sh NAME PLAN MAP FEED [extra kit args]
set -u
N=$1; PLAN=$2; R=$3; F=$4; shift 4
W=/srv/opentallas-scratch2/claude/wt/die-qc4-1028; B=/srv/opentallas-scratch2/claude/die-qc4-1028; D=$B/$N; O=$D/trial
mkdir -p $D; log(){ echo "kit $N: $* $(date)" >> $B/chain.log; }
log "START code $(git -C $W rev-parse --short HEAD) plan $(sha256sum $PLAN | cut -c1-12) map $R feed $F args $*"
cd $W && python3 -I $W/tools/die_plan/die_trial.py kit $PLAN --out $O --region-trees $R --feed $F --tree-form link_htree --rep-um 250 --tree-site-legal --tree-site-slide --leaf-um 200 "$@" > $D/kit.log 2>&1; log "kit rc $?"
cd $O && bash run_clock.sh > $D/clock_run.log 2>&1; log "clock rc $?"
mkdir -p $D/clk; cp $O/clock/{ctree.v,ctree.tcl,tree.json} $D/clk/

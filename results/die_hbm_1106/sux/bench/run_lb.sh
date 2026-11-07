#!/bin/bash
# usage: run_lb.sh KIT TAG : offline replay of sux_latbal.tcl on KIT 4_cts.odb (placement RC, TT), no write
K=$1; T=$2; E=/srv/opentallas-scratch3/claude/hbm-form-split-14-sux/sk
B=$(ls -d $K/run/results/asap7/*/base); O=$E/lb_$T; rm -rf $O; mkdir -p $O/work
rsync -a --exclude run --exclude signoff --exclude lec --exclude views --exclude face_shell_work $K/ $O/work/
head -n 193 $K/postcts_gate.tcl > $O/lb.tcl
echo 'namespace eval sux {}; set ::sux::offline 1; source /out/sux_latbal.tcl' >> $O/lb.tcl
cp $E/sux_latbal.tcl $O/
docker run -d --rm --memory 24g --name suxlb_$T -e OT_CORNER=TT -e ODB=/base/4_cts.odb -e OT_SUX_LB_ROUNDS=${ROUNDS:-8} -v $B:/base:ro -v $O:/out -v $O/work:/work openroad/orfs:latest bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /out/lb.tcl > /out/lb.log 2>&1"

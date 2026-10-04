#!/bin/bash
# Chained after each QPIPE run (detached): post-CTS SS screen when 4_1_cts.odb appears, then on completion SS setup and
# FF hold on the routed database with its SPEF.  usage: post_sta.sh RUN WT
R=$1; WT=$2
J=/home/ubuntu/otjobs/dsrom_qpipe_20261003/$R
S=/srv/opentallas-scratch/claude/dsrom-qpipe/sta/$R; mkdir -p $S
TCL=/srv/opentallas-scratch/claude/dsrom-qpipe/sta_corner.tcl
sta() { # name corner odb sdc spef
  docker run --rm -v /home/ubuntu/otjobs:/home/ubuntu/otjobs -v /srv/opentallas-scratch:/srv/opentallas-scratch -v $WT:/src \
   -e CORNER=$2 -e ODB=$3 -e SDC=$4 -e SPEF=$5 -e OUT=$S/$1 openroad/orfs:latest \
   bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $TCL" > $S/$1.log 2>&1; echo $? > $S/$1.rc; }
B() { ls -d $J/work/orfs/results/asap7/*/base 2>/dev/null | head -1; }
until [ -n "$(B)" ] && [ -f "$(B)/4_1_cts.odb" ] || [ -f $J/launch.done ]; do sleep 60; done
[ -f "$(B)/4_1_cts.odb" ] && sta cts_SS SS $(B)/4_1_cts.odb $(B)/4_cts.sdc ""
until [ -f $J/launch.done ]; do sleep 120; done
if [ -f "$(B)/6_final.odb" ]; then
  sta final_SS SS $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef &
  sta final_FF FF $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef &
  wait
fi
echo done > $S/post.done

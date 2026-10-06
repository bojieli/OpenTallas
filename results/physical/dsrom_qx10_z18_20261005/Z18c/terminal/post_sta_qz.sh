#!/bin/bash
# post-CTS SS screen, then post-route SS setup / FF hold (run SDC + SPEF) and the top-300 path dumps (classify.tcl)
R=$1; WT=$2
J=/srv/opentallas-scratch/claude/dsrom-qtclose/jobs/$R
S=/srv/opentallas-scratch/claude/dsrom-qtclose/sta/$R; mkdir -p $S
T=/srv/opentallas-scratch/claude/dsrom-qtclose
sta() { # name corner odb sdc spef tcl
  docker run --rm -v /srv/opentallas-scratch:/srv/opentallas-scratch -v $WT:/src -e NPATH=300 \
   -e CORNER=$2 -e ODB=$3 -e SDC=$4 -e SPEF=$5 -e OUT=$S/$1 openroad/orfs:latest \
   bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $6" > $S/$1.log 2>&1; echo $? > $S/$1.rc; }
B() { ls -d $J/work/orfs/results/asap7/*/base 2>/dev/null | head -1; }
until [ -n "$(B)" ] && [ -f "$(B)/4_1_cts.odb" ] || [ -f $J/launch.done ]; do sleep 60; done
[ -f "$(B)/4_1_cts.odb" ] && sta cts_SS SS $(B)/4_1_cts.odb $(B)/4_cts.sdc "" $T/sta_corner.tcl
until [ -f $J/launch.done ]; do sleep 120; done
if [ -f "$(B)/6_final.odb" ]; then
  sta final_SS SS $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $T/sta_corner.tcl &
  sta final_FF FF $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $T/sta_corner.tcl &
  sta cls_SS SS $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $T/classify.tcl &
  sta cls_FF FF $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $T/classify.tcl &
  sta io_SS SS $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $T/io.tcl &
  sta io_FF FF $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $T/io.tcl &
  wait
fi
echo done > $S/post.done

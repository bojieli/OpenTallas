#!/bin/bash
# CORELAT-SQ-1 collect: clock-pin -> reg CK insertion on <mod>/run/.../4_cts.odb, TT+FF, placement RC from kit setRC_rcx.tcl
B=/srv/opentallas-scratch2/claude/corelat-sq-1; M=$B/meas
for m in "$@"; do K=$B/cts/$m; R=$(ls -d $K/run/results/asap7/*/base); R=/kit/${R#$K/}
  [ -f $K/${R#/kit/}/4_cts.odb ] || { echo "$m: no 4_cts.odb yet"; continue; }
  XL=$(ls $K/macros/*_tt.lib 2>/dev/null | sed "s#$K#/kit#" | tr "\n" " "); XF=$(ls $K/macros/*_ff.lib 2>/dev/null | sed "s#$K#/kit#" | tr "\n" " ")
  for c in TT FF; do X=$XL; [ $c = FF ] && X=$XF
    docker run --rm --cpus=2 --memory=16g -v $K:/kit:ro -v $M:/meas -e OT_CORNER=$c -e ODB=$R/4_cts.odb -e SDC=$R/4_cts.sdc -e SPEF= -e RC=/kit/setRC_rcx.tcl -e "XLIBS=$X" -e OUT=/meas/${m}_$c.tsv openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /meas/ins.tcl > /meas/${m}_$c.log 2>&1; chmod a+rw /meas/*"
  done; python3 -I /srv/opentallas-scratch2/claude/wt/die-s81-8/results/die_s81_8_1028/scripts/corelat_stats.py $M/${m}_TT.tsv $M/${m}_FF.tsv
done

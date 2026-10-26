#!/bin/bash
WT=/srv/opentallas-scratch2/claude/wt/path-hbm-q3-1025; D=/srv/opentallas-scratch2/claude/path-hbm/q3split
/usr/bin/time -v python3 $WT/physical/die_plan/hbm/cores/harden/build_split_tops.py --net ${NET:-$D/net} --only "$1" > $D/bst_$2.log 2>&1
echo "bst $2 rc=$?"

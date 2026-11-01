#!/bin/bash
# rekit2.sh form with the dh53-l48z worktree tools: pass1 before_private.sv -> published <module>.sv; pass2 must match
set -u; D=/srv/opentallas-scratch2/claude/die-head-48; S=$D/head_source_l48z; O=$D/dh53/l48z/rtlgen_$1; RK=/srv/opentallas-scratch2/claude/die-head-46/head_rekit_current.py; W=/srv/opentallas-scratch2/claude/wt/dh53-l48z
rm -rf $O; python3 $RK $W $S $O $1 > $O.p1.log 2>&1
if [ -f $O/before_private.sv ]; then cp $O/before_private.sv $S/$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[\"partition_types\"][sys.argv[2]][\"module\"])" $S/source_plan.json $1).sv; rm -rf $O; python3 $RK $W $S $O $1 > $O.p2.log 2>&1; echo "$1 p2 rc=$?"; else echo "$1 p1 no before_private"; tail -3 $O.p1.log; fi

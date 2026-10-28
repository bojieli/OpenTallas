#!/bin/bash
# try.sh NAME [--tree-opt k=v ...]: kit (link_forward) + stage-model landed margin
N=$1; shift; W=/srv/opentallas-scratch2/claude/wt/land-head-3; B=/srv/opentallas-scratch2/claude/land-head-3; J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
cd $W && python3 tools/die_plan/die_trial.py kit $J --out $B/$N/kit --tree-form ${FORM:-link_forward} --tree-site-slide "$@" > $B/$N.kit.log 2>&1 || { tail -15 $B/$N.kit.log; exit 1; }
python3 -c "import json;k=json.load(open(\"$B/$N/kit/kit.json\"));ct=k[\"clock_tree\"];print(ct[\"link_dme\"], \"fallbacks\", ct[\"site_legal\"][\"slide_fallbacks\"], \"wire\", ct[\"wire_um\"], \"rep\", ct[\"repeaters\"])"
cd $B && python3 $W/tools/s81_head/landed_topo_model.py $J $N/kit/clock model_$N --tools $W/tools/die_plan > model_$N.log 2>&1; python3 cat2.py model_$N $J 8

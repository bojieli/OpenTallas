#!/bin/bash
# plan-only: islands + tree model for old (R4b) and F3 geometry; run on a fleet host
set -euo pipefail
W=${W:-/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor}; R=$(dirname "$(readlink -f "$0")"); T=$R/../../../tools/die_plan
cd $W
# validation: R5 btab geometry + R5 islands must reproduce the R5 plan model (TT 277.49 / FF 226.37)
[ -f btab.geo ] && python3 $R/su_tree_model.py btab.geo val_btab_r5.tcl 70 "" $W > val_btab_r5.log 2>&1 || true
for t in vmr rp1; do
  python3 $R/refloor.py $t.geo ${t}_f3.geo > ${t}_f3.log
  python3 -c "
import sys,json;sys.path.insert(0,'$T');import core_islands as C
for g in ('$t.geo','${t}_f3.geo'):
  r=C.site(C.read_geo(g),4,110.0);json.dump(r,open(g+'.isl.json','w'),indent=1)
  print(g,r['verdict'],r['entry_maze_um'],'equal_path',r['equal_path_um'],'floor',r['floor_entry_to_sink_maze_um'],[q['centre_um'] for q in r['islands']])
" >> islands.log
  for g in $t ${t}_f3; do python3 $R/su_tree_model.py $g.geo $g.tree.tcl 70 $g.geo.isl.json $W > $g.model.log 2>&1 & done
done
wait

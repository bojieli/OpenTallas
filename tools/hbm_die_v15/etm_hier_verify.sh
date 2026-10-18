#!/bin/bash
# HBM-IDXETM (2026-10-18): verify the hierarchical SYNTH ETM (synth_etm_hier.sh) against the flat one on a REDUCED
# configuration of the same mapped netlist: ONE ot_hbm_idx_engine_static (4 x ot_hbm_idx_chunk_owned_native + tail,
# 9.21 M flat cells; idx_score = 4 engines) extracted as top idxeng_red.  Builds
#   red_flat  flat ETM (same OpenSTA build)        red_h0  hier, child characterised without clock uncertainty
#   red_h1    hier, child with the parent's uncertainty (60/25 ps; would count it twice if baked into the child arcs)
# and compares every arc (etm_lib_compare.py) of h0/h1 vs flat at TT and FF.  Verdict lines OT_ETM_COMPARE.
#   etm_hier_verify.sh <bundle dir with tools/ and full/<name>.netlist.v> <name>
set -u
B=$(readlink -f $1); NAME=$2; T=$B/tools
python3 - $B/full/$NAME.netlist.v > $B/engine_module.txt <<'PY'
import re, sys
t = open(sys.argv[1]).read()
print(re.search(r'(?m)^module (\\\S*ot_hbm_idx_engine_static\S*)', t).group(1), end='')
PY
for v in red_flat red_h0 red_h1; do
  rm -rf $B/$v; mkdir -p $B/$v
  python3 $T/etm_hier_split.py extract $B/full/$NAME.netlist.v "$(cat $B/engine_module.txt)" idxeng_red $B/$v/red.netlist.v || exit 2
  echo 'hierarchy -check -top idxeng_red' > $B/$v/red.ys; echo '{"macros": []}' > $B/$v/red.files.json
done
MEMG=${CHILD_MEMG:-20} ETM_CHILD_UNC=0 bash $T/synth_etm_hier.sh $B $B/red_h0 red ot_hbm_idx_chunk_owned_native; r0=$?
MEMG=${CHILD_MEMG:-20} ETM_CHILD_UNC=1 bash $T/synth_etm_hier.sh $B $B/red_h1 red ot_hbm_idx_chunk_owned_native; r1=$?
MEMG=${FLAT_MEMG:-44} bash $T/synth_etm_hier.sh $B $B/red_flat red -; rf=$?
echo "OT_ETM_HIER_VERIFY_RC flat=$rf h0=$r0 h1=$r1"
for h in red_h0 red_h1; do for c in tt ff; do
  echo "== $h $c"; python3 $T/etm_lib_compare.py $B/red_flat/idxeng_red_synth_$c.lib $B/$h/idxeng_red_synth_$c.lib --json $B/cmp_${h}_$c.json
done; done
for v in red_flat red_h0 red_h1; do echo "== $v worst TT"; grep -m3 -E 'slack|data arrival' $B/$v/hier/etm_worst_top_tt.rpt; done

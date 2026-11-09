cd /srv/opentallas-scratch2/claude/s81-types-10/leafbatch
P=/srv/opentallas-scratch3/claude/kw34/wave_cg_frz_xrt/physical/die_plan/s81/plan_h2_2249.json
mkdir -p mp
for d in in/ot_*; do it=$(basename $d); [ -s $d/conn.json ] || { echo "$it NO conn"; continue; }
 EO_QUIET=1 timeout 300 python3 -I escape_open.py $P $it $d/macro_place.tcl $d/io.tcl --conn $d/conn.json --target 0.85 --apply mp/$it.macro_place.tcl --json mp/$it.json > mp/$it.out 2> mp/$it.err
 rc=$?; python3 -I -c "
import json,sys
try:
  d=json.load(open('mp/$it.json')); print('$it',$rc,'worst',d['before']['worst'],'->',d['after']['worst'],'hot',d['before']['hot'],'->',d['after']['hot'],'moves',len(d['moves']),'blk',len(d['blockages']),'bus',d['bus_cost_rise_pct'],'stregs',d['station_regs_under_macros'],'|',d['after']['top'][0] if d['after']['top'] else '')
except Exception as e: print('$it rc=$rc ERR',e, open('mp/$it.err').read()[-200:].replace(chr(10),' '))
"; done

cd /srv/opentallas-scratch2/claude/s81-types-10/leafbatch
P=/srv/opentallas-scratch3/claude/kw34/wave_cg_frz_xrt/physical/die_plan/s81/plan_h2_2249.json
sed 's/^MAXSTEP = 12; BUSCAP = 0.15/MAXSTEP = 40; BUSCAP = 0.40/' escape_open.py > escape_open_b.py; grep -c 'BUSCAP = 0.40' escape_open_b.py
mkdir -p mpb
for it in "$@"; do d=in/$it; [ -s $d/conn.json ] || continue
 EO_QUIET=1 timeout 300 python3 -I escape_open_b.py $P $it $d/macro_place.tcl $d/io.tcl --conn $d/conn.json --target 0.85 --apply mpb/$it.macro_place.tcl --json mpb/$it.json > mpb/$it.out 2> mpb/$it.err
 python3 -I -c "
import json
d=json.load(open('mpb/$it.json')); print('$it','worst',d['before']['worst'],'->',d['after']['worst'],'hot',d['after']['hot'],'moves',len(d['moves']),'bus',d['bus_cost_rise_pct'],'|',d['after']['top'][:2])"
done

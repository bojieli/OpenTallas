cd /srv/opentallas-scratch2/claude/s81-types-10/leafbatch
P=/srv/opentallas-scratch3/claude/kw34/wave_cg_frz_xrt/physical/die_plan/s81/plan_h2_2249.json
python3 -I - <<'PY'
s=open('escape_open.py').read()
needle="base = {k: list(v) for k, v in pos.items()}; cur = {k: list(v) for k, v in pos.items()}\n"
assert needle in s
add=needle+"for n in cur:\n    w = legal_why(n, cur)\n    if w: print('ILLEGAL', n, w, flush=True)\n"+"bad=[(a,b) for a in cur for b in cur if a<b and touch(a,b,cur)]\nprint('GAP_CONFLICTS',bad,flush=True)\n"
open('escape_open_c.py','w').write(s.replace(needle,add))
PY
it=$1; shift; mkdir -p mph
python3 -I hand.py mp/$it.macro_place.tcl mph/$it.base.tcl "$@"
EO_QUIET=1 python3 -I escape_open_c.py $P $it mph/$it.base.tcl in/$it/io.tcl --conn in/$it/conn.json --target 0.85 --apply mph/$it.macro_place.tcl --json mph/$it.json 2>&1 | grep -E 'ILLEGAL|GAP_CONFLICTS' | cut -c1-220
python3 -I -c "
import json
d=json.load(open('mph/$it.json')); print('$it after worst',d['after']['worst'],'hot',d['after']['hot'],'newmoves',len(d['moves']),'bus',d['bus_cost_rise_pct'],'stregs',d['station_regs_under_macros']); print(d['after']['top'][:4])"

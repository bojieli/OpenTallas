cd /
W=/srv/opentallas-scratch2/claude/s81-types-13/leaf; IT=ot_s81sl_leaf__t7; I=$W/in/$IT
P=/srv/opentallas-scratch3/claude/kw34/wave_cg_frz_xrt/physical/die_plan/s81/plan_h2_2249.json
cat $I/macro_moves.json | cut -c1-500; echo
python3 -I $W/eo_band.py $P $IT $I/macro_place.tcl $I/io.tcl --conn $I/conn.json --apply $W/mp13/$IT.tcl --json $W/mp13/$IT.json > $W/mp13/$IT.out 2> $W/mp13/$IT.err; echo rc=$?
tail -3 $W/mp13/$IT.err | cut -c1-200
grep -nE "GAP_CONFLICTS|worst|ratio|before|after|bus|moved|target" $W/mp13/$IT.out | head -30 | cut -c1-200
python3 -I - <<PY
import json
d=json.load(open("$W/mp13/$IT.json"))
print([k for k in d])
for k in ("hot_before","hot_after","worst_before","worst_after","moved","bus_rise","moves","n_moves","blockages","gap_conflicts"):
    if k in d: print(k, str(d[k])[:400])
PY
cd $W && python3 -I mk3b.py $IT=mp13/$IT.tcl | cut -c1-700

#!/bin/bash
# run_h10r2.sh : R2-APRON port on the 4 col_h10_r2 types of ready7 -> aug4/plan_h10r2.json + taps + route_supply
W=/srv/opentallas-scratch2/claude/vislayout2-s81/w; R=$W/../repo; T=$W/../tools; cd $W
S=/srv/opentallas-scratch2/claude/kw43/src_t51f_pbp_por15c_por36
rm -rf h10r2; mkdir -p h10r2
TS="col_h10_r2__t1__cl1f5d6c2a col_h10_r2__t1__cl99efd374 col_h10_r2__t1__cl8b686b3e col_h10_r2__t1__clac068e56"
# core_conns for these types: the R2 netlist-augmented entry (same module family) where the plan's own is missing
cp ready7.json aug4/h10_tmp.json
python3 -I - aug4/h10_tmp.json $TS <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
for t in sys.argv[2:]:
    for i, a in enumerate(p["partition_types"][t]["clock"].get("added_taps") or []):
        a["xy"] = [1425.6, 300.0 + 34.56 * i]          # parked during core_place, restored below
json.dump(p, open(sys.argv[1], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/seed_h10r2.py aug4/h10_tmp.json $t h10r2/seed_$t.json; done
python3 -I -c "
import json,glob;d={}
for f in glob.glob('h10r2/seed_*.json'): d.update(json.load(open(f)))
json.dump(d,open('h10r2/seed.json','w'),indent=1)"
OMP_NUM_THREADS=8 python3 -I $R/tools/die_plan/core_place_vl2.py $W/aug4/h10_tmp.json --die s81 --repo $R --types $(echo $TS | tr " " ",") --seed h10r2/seed.json --no-search --gap auto --accept-timing --out-plan $W/aug4/plan_h10r2_pre.json --event $W/h10r2/ev.json --svg $W/h10r2/svg > h10r2/log.txt 2>&1
grep -E "seed:|^col|Traceback|Error" h10r2/log.txt | cut -c1-250
python3 -I - ready7.json aug4/plan_h10r2_pre.json aug4/plan_h10r2.json $TS <<'PY'
import json, sys
b = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2]))
for t in sys.argv[4:]:
    p["partition_types"][t]["clock"]["added_taps"] = b["partition_types"][t]["clock"]["added_taps"]
json.dump(p, open(sys.argv[3], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/taptune.py $S aug4/plan_h10r2.json $t aug4/plan_h10r2.json L | grep legalise; done
for t in $TS; do echo "## $t"; python3 -I $T/taptune.py $S aug4/plan_h10r2.json $t aug4/plan_h10r2.json 2>&1 | grep -E "^now|^round|Trace|Error" | cut -c1-120; python3 -I $T/taptune.py $S aug4/plan_h10r2.json $t | cut -c1-12; done
for t in $TS; do python3 -I $R/tools/die_plan/route_supply.py $W/aug4/plan_h10r2.json --die s81 --repo $R --types $t --grt-halving edge_outline --out $W/rs/h10_$t >/dev/null 2>&1; tail -1 rs/h10_$t/route_supply_s81.tsv | cut -f2,3,5,8,9,10; done
sha256sum aug4/plan_h10r2.json | cut -c1-12
echo H10_DONE

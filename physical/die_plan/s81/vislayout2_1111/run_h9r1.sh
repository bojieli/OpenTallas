#!/bin/bash
# run_h9r1.sh : R2-APRON port on the 4 col_h10_r2 types of ready7 -> aug4/plan_h9r1.json + taps + route_supply
W=/srv/opentallas-scratch2/claude/vislayout2-s81/w; R=$W/../repo; T=$W/../tools; cd $W
S=/srv/opentallas-scratch2/claude/kw43/src_t51f_pbp_por15c_por36
rm -rf h9r1; mkdir -p h9r1
TS="col_h9_r1__t1__cl49d7a23e col_h9_r1__t1__clf32cde8d"
# core_conns for these types: the R2 netlist-augmented entry (same module family) where the plan's own is missing
cp ready7.json aug4/h9r1_tmp.json
python3 -I - aug4/h9r1_tmp.json $TS <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
for t in sys.argv[2:]:
    for i, a in enumerate(p["partition_types"][t]["clock"].get("added_taps") or []):
        a["xy"] = [1425.6, 300.0 + 34.56 * i]          # parked during core_place, restored below
json.dump(p, open(sys.argv[1], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/seed_h9r1.py aug4/h9r1_tmp.json $t h9r1/seed_$t.json; done
python3 -I -c "
import json,glob;d={}
for f in glob.glob('h9r1/seed_*.json'): d.update(json.load(open(f)))
json.dump(d,open('h9r1/seed.json','w'),indent=1)"
OMP_NUM_THREADS=8 python3 -I $R/tools/die_plan/core_place_vl2.py $W/aug4/h9r1_tmp.json --die s81 --repo $R --types $(echo $TS | tr " " ",") --seed h9r1/seed.json --no-search --gap auto --accept-timing --allow-need-more 4 --out-plan $W/aug4/plan_h9r1_pre.json --event $W/h9r1/ev.json --svg $W/h9r1/svg > h9r1/log.txt 2>&1
grep -E "seed:|^col|Traceback|Error" h9r1/log.txt | cut -c1-250
python3 -I - ready7.json aug4/plan_h9r1_pre.json aug4/plan_h9r1.json $TS <<'PY'
import json, sys
b = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2]))
for t in sys.argv[4:]:
    p["partition_types"][t]["clock"]["added_taps"] = b["partition_types"][t]["clock"]["added_taps"]
json.dump(p, open(sys.argv[3], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/taptune.py $S aug4/plan_h9r1.json $t aug4/plan_h9r1.json L | grep legalise; done
for t in $TS; do echo "## $t"; python3 -I $T/taptune.py $S aug4/plan_h9r1.json $t aug4/plan_h9r1.json 2>&1 | grep -E "^now|^round|Trace|Error" | cut -c1-120; python3 -I $T/taptune.py $S aug4/plan_h9r1.json $t | cut -c1-12; done
for t in $TS; do python3 -I $R/tools/die_plan/route_supply.py $W/aug4/plan_h9r1.json --die s81 --repo $R --types $t --grt-halving edge_outline --out $W/rs/h9r1_$t >/dev/null 2>&1; tail -1 rs/h9r1_$t/route_supply_s81.tsv | cut -f2,3,5,8,9,10; done
sha256sum aug4/plan_h9r1.json | cut -c1-12
echo H9R1_DONE

#!/bin/bash
# run_r0.sh VAR TYPES... : COL-H9R0 form of ready7 -> aug4/plan_${D}.json + taps + route_supply
W=/srv/opentallas-scratch2/claude/vislayout2-s81/w; R=$W/../repo; T=$W/../tools; cd $W
S=/srv/opentallas-scratch2/claude/kw43/src_t51f_pbp_por15c_por36
V=$1; shift; TS="$*"; D=r0_$V${TAG:-}
rm -rf $D; mkdir -p $D
# core_conns for these types: the R2 netlist-augmented entry (same module family) where the plan's own is missing
cp ready7.json aug4/${D}_tmp.json   # in aug4/: the netlist-augmented core_conns.json applies
python3 -I - aug4/${D}_tmp.json $TS <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
for t in sys.argv[2:]:
    for i, a in enumerate(p["partition_types"][t]["clock"].get("added_taps") or []):
        a["xy"] = [1425.6, 300.0 + 34.56 * i]          # parked during core_place, restored below
json.dump(p, open(sys.argv[1], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/seed_r0.py aug4/${D}_tmp.json $t $D/seed_$t.json $V; done
python3 -I -c "
import json,glob;d={}
for f in glob.glob('$D/seed_*.json'): d.update(json.load(open(f)))
json.dump(d,open('$D/seed.json','w'),indent=1)"
OMP_NUM_THREADS=8 python3 -I $R/tools/die_plan/core_place_vl2.py $W/aug4/${D}_tmp.json --die s81 --repo $R --types $(echo $TS | tr " " ",") --seed $D/seed.json --no-search --gap auto --accept-timing --allow-need-more "${NM:-}" --out-plan $W/aug4/plan_${D}_pre.json --event $W/$D/ev.json --svg $W/$D/svg > $D/log.txt 2>&1
grep -E "seed:|^col|Traceback|Error" $D/log.txt | cut -c1-250
python3 -I - ready7.json aug4/plan_${D}_pre.json aug4/plan_${D}.json $TS <<'PY'
import json, sys
b = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2]))
for t in sys.argv[4:]:
    p["partition_types"][t]["clock"]["added_taps"] = b["partition_types"][t]["clock"]["added_taps"]
json.dump(p, open(sys.argv[3], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/taptune.py $S aug4/plan_${D}.json $t aug4/plan_${D}.json L | grep legalise; done
for t in $TS; do echo "## $t"; python3 -I $T/taptune.py $S aug4/plan_${D}.json $t aug4/plan_${D}.json 2>&1 | grep -E "^now|^round|Trace|Error" | cut -c1-120; python3 -I $T/taptune.py $S aug4/plan_${D}.json $t | cut -c1-12; done
for t in $TS; do python3 -I $R/tools/die_plan/route_supply.py $W/aug4/plan_${D}.json --die s81 --repo $R --types $t --grt-halving edge_outline --out $W/rs/${D}_$t >/dev/null 2>&1; tail -1 rs/${D}_$t/route_supply_s81.tsv | cut -f2,3,5,8,9,10; done
sha256sum aug4/plan_${D}.json | cut -c1-12
echo ${D}_DONE

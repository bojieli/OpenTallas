#!/bin/bash
# run_h10r1.sh VAR : VISLAYOUT2-S81/H10R1 seed VAR on the 2 col_h10_r1 types of the ready7 head (580d790a93c3)
# -> $W/aug4/h10r1_plan_VAR.json + taps + route_supply edge_outline (ring-bin fix)
set -u; cd /
X=/srv/opentallas-scratch2/claude/vislayout2-s81/sub/h10r1; W=/srv/opentallas-scratch2/claude/vislayout2-s81/w
R=$X/repo; T=$X/tools; O=$X/w; A=$W/aug4; VAR=$1; D=$O/$VAR; NM=${NM:-}
S=/srv/opentallas-scratch2/claude/kw43/src_t51f_pbp_por15c_por36
TS="col_h10_r1__t1__cl95b37463 col_h10_r1__t1__cld01bb4ae"
rm -rf $D; mkdir -p $D
cp $O/ready7_head.json $A/h10r1_${VAR}_tmp.json
python3 -I - $A/h10r1_${VAR}_tmp.json $TS <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
for t in sys.argv[2:]:
    for i, a in enumerate(p["partition_types"][t]["clock"].get("added_taps") or []):
        a["xy"] = [1425.6, 300.0 + 34.56 * i]          # parked during core_place, restored below
json.dump(p, open(sys.argv[1], "w"), indent=1)
PY
for t in $TS; do python3 -I $T/seed_h10r1.py $A/h10r1_${VAR}_tmp.json $t $D/seed_$t.json $VAR; done
python3 -I -c "
import json,glob;d={}
for f in glob.glob('$D/seed_*.json'): d.update(json.load(open(f)))
json.dump(d,open('$D/seed.json','w'),indent=1)"
OMP_NUM_THREADS=8 python3 -I $R/tools/die_plan/core_place_vl2.py $A/h10r1_${VAR}_tmp.json --die s81 --repo $R --types $(echo $TS | tr " " ",") --seed $D/seed.json --no-search --gap auto --accept-timing --allow-need-more "$NM" --out-plan $A/h10r1_plan_${VAR}_pre.json --event $D/ev.json --svg $D/svg > $D/log.txt 2>&1
grep -E "seed:|^col|Traceback|Error|need_more|legal" $D/log.txt | cut -c1-250 | head -30
python3 -I - $O/ready7_head.json $A/h10r1_plan_${VAR}_pre.json $A/h10r1_plan_${VAR}.json $TS <<'PY'
import json, sys
b = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2]))
for t in sys.argv[4:]:
    if "added_taps" in b["partition_types"][t]["clock"]:
        p["partition_types"][t]["clock"]["added_taps"] = b["partition_types"][t]["clock"]["added_taps"]
json.dump(p, open(sys.argv[3], "w"), indent=1)
PY
for t in $TS; do python3 -I -c "import json,sys;sys.exit(0 if json.load(open('$A/h10r1_plan_${VAR}.json'))['partition_types']['$t']['clock'].get('added_taps') else 1)" || { echo "## $t no added_taps (grid taps only)"; continue; }; python3 -I $T/taptune.py $S $A/h10r1_plan_${VAR}.json $t $A/h10r1_plan_${VAR}.json L | grep legalise; echo "## $t"; python3 -I $T/taptune.py $S $A/h10r1_plan_${VAR}.json $t $A/h10r1_plan_${VAR}.json 2>&1 | grep -E "^now|^round|Trace|Error" | cut -c1-120; python3 -I $T/taptune.py $S $A/h10r1_plan_${VAR}.json $t | cut -c1-12; done
for t in $TS; do python3 -I $R/tools/die_plan/route_supply.py $A/h10r1_plan_${VAR}.json --die s81 --repo $R --types $t --grt-halving edge_outline --out $O/rs/${VAR}_$t >/dev/null 2>&1; tail -1 $O/rs/${VAR}_$t/route_supply_s81.tsv | cut -f2,3,5,6,8,9,10,11; done
sha256sum $A/h10r1_plan_${VAR}.json | cut -c1-12
echo H10R1_DONE $VAR

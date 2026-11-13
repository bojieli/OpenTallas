#!/bin/bash
# run_types.sh TYPES_FILE OUTDIR : seed -> park taps -> core_place (seed only) -> street check (full list)
W=${W:-/srv/opentallas-scratch3/claude/wt/frame-forms-1}; F=${F:-/srv/opentallas-scratch3/claude/frame-forms-1}; E=$W/events/s81_frame_spine_1113; cd $F
T=$(cat $1); O=$F/$2; rm -rf $O; mkdir -p $O
python3 -I $E/frame_spine_seed.py w/plan_A.json w/seed_all.json --conns $W/physical/die_plan/s81/core_conns.json --report w/seed_rep.json > w/seed.log
python3 -I $E/park_taps.py w/plan_A.json w/seed_all.json w/plan_A_tp.json
OMP_NUM_THREADS=8 nice python3 -I $E/cp_frame.py $W/tools/die_plan $F/w/plan_A_tp.json --die s81 --repo $W --types $T --seed $F/w/seed_all.json --no-search --gap 0.5 --reach 395 --out-plan $O/plan.json --event $O/ev.json --svg $O/svg > $O/log.txt 2>&1; echo rc=$?
grep -E "SEED|no legal|Trace|Error" $O/log.txt | cut -c1-200 | head -20; grep -P "^col_h.*\t(True|False)\t" $O/log.txt | cut -f1,2,3,15,16 
cd $F/srfull/die_plan && nice python3 -I street_rule.py check $O/plan.json --die s81 --repo $W --types $T --out $O/street_full.json 2>&1 | tail -4
python3 -I - <<PY
import json,collections
d=json.load(open("$O/street_full.json"))
for r in d["rows"]:
    for it in r.get("worst") or []:
        if it.get("kind") not in ("sliver","outline_sliver"):
            print(r["type"][4:24], json.dumps({a:b for a,b in it.items() if a not in ("free_spans","pin_reorder","same_cluster")})[:230])
PY

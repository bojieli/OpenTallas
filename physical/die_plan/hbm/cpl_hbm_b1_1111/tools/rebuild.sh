#!/bin/bash
# CPL-HBM-B1: lad.py on the six types -> CAND/die_plan.json (t19 + types + note) -> per-partition cut budget vs t19. usage: rebuild.sh CAND
set -eu; B=/srv/opentallas-scratch3/claude/cpl-hbm-b1/lad; cd $B; C=$1
for t in q_b001 q_b001__physical_v1 q_b010 q_b010__physical_v1 q_b011 q_b011__physical_v1; do
  nice -n 19 python3 -I lad.py t19/die_plan.json $t spec.json out/$t.json ../tr/${t%__physical_v1}.json > out/$t.log 2>&1 || { echo "LAD FAIL $t"; tail -5 out/$t.log; }
  grep '^{' out/$t.log | tail -1 | cut -c1-700
done
mkdir -p $C; [ -e $C/.keep ] || cp -al t19/. $C/; rm -f $C/die_plan.json $C/die_plan.json.gz
python3 -I - $C <<'PY'
import json, sys
C = sys.argv[1]; P = json.load(open("t19/die_plan.json"))
NOTE = (" | CPL-HBM-B1 hcol S2 1111 (on t19 ladder outline): idx stacks re-packed as frames (h0 ra+rb+h1 adjacent, bound h0->h1 centre <= 405 um), "
        "positions only; register counts unchanged, covered ft/plan-station register sites re-sited (hops <= 405); frame rows placed between "
        "250-um die cut lines so no partition cut segment ratio rises above max(0.6, t19)")
for t in ("q_b001", "q_b001__physical_v1", "q_b010", "q_b010__physical_v1", "q_b011", "q_b011__physical_v1"):
    o = json.load(open(f"out/{t}.json")); o["note"] = o.get("note", "") + NOTE; P["partition_types"][t] = o
json.dump(P, open(f"{C}/die_plan.json", "w"), indent=1)
PY
cd wt/tools/die_plan && nice -n 19 python3 -I cutpart_cplb1.py ../../../$C/die_plan.json ../../../$C.cut.json NW_b001,NW_b010,NW_b011,NE_b001,NE_b010,NE_b011 >/dev/null
cd $B && python3 -I budget.py t19/die_plan.json t19.cut.json $C.cut.json | grep -c . && python3 -I budget.py t19/die_plan.json t19.cut.json $C.cut.json | grep OVER || echo "NO OVER"

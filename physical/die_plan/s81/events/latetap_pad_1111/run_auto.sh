#!/bin/bash
# DS85-LATETAP-1111 (DO_NOT_COUNT): DIE-RECHECK-1 s81_clock_auto.sh recipe (feed_bal regen + kit + post_kit) on a variant
#   run_auto.sh VARIANT PLAN_NAME [TAP_PAD.json]   (s81/auto/VARIANT/repo holds tools + physical/die_plan/s81/PLAN_NAME)
set -uo pipefail
cd /
W=/srv/opentallas-scratch2/claude/ds85-latetap
V=$1; A=$W/s81/auto/$V; PAD=${3:-}
REPO=$A/repo; PLAN=$REPO/physical/die_plan/s81/$2; TOOLS=$REPO/tools/die_plan
echo "auto $V plan $PLAN pad ${PAD:-none} $(date)" > $A/auto.log
python3 -I - "$PLAN" "$A/map.json" <<"PY" >> $A/auto.log 2>&1 || { echo FAIL map >> $A/auto.log; exit 21; }
import json, sys
d = json.load(open(sys.argv[1]))
json.dump({"part_region": {x["name"]: x["name"] for x in d["partitions"]}}, open(sys.argv[2], "w"))
print("regions", len(d["partitions"]))
PY
sed -e "s#^  plan: .*#  plan: $PLAN#" -e "s#^  region_map: .*#  region_map: $A/map.json#" -e "s#^  feed: .*#  feed: $A/feed_bal.json#" \
  $W/s81/cfg/s81_recheck_bal.yaml > $A/kit.yaml
if [ -n "$PAD" ]; then
  python3 -I - $A/kit.yaml $PAD <<"PY" || exit 25
import sys
p, t = sys.argv[1:3]; s = open(p).read(); k = "\nresidual:\n  snake: all\n  cell_paths: true\n"
assert k in s and "tap_pad" not in s
open(p, "w").write(s.replace(k, k + "  tap_pad: %s   # DS85-LATETAP-1111 (12.8d2 residual tap pads)\n" % t))
PY
fi
AVOID=""
for try in 1 2 3 4; do
  python3 -s $W/scripts/feed_bal.py $PLAN $TOOLS $A/feed_bal.json --avoid "$AVOID" --phy-parents $W/s81/cfg/feed_sb6_h2_2249.json >> $A/auto.log 2>&1 || { echo FAIL feed >> $A/auto.log; exit 22; }
  rm -rf $W/s81/ck_$V
  python3 -s $REPO/tools/clk/ot_clk.py kit $A/kit.yaml --out $W/s81/ck_$V --workers 24 > $A/kit.log 2>&1 && break
  E=$(python3 -I $W/scripts/reach_edge.py $A/kit.log $A/feed_bal.json)
  [ -n "$E" ] || { echo "FAIL kit (try $try, not a feed-leg reach failure)" >> $A/auto.log; exit 23; }
  echo "kit try $try: reach failure on feed edge $E -> avoid" >> $A/auto.log
  AVOID="${AVOID:+$AVOID,}$E"
  [ $try = 4 ] && { echo FAIL kit after 4 tries >> $A/auto.log; exit 23; }
done
echo "kit ok, avoid=[$AVOID]" >> $A/auto.log
PLAN=$PLAN TOOLS=$TOOLS AUTO=1 $W/scripts/post_kit.sh $V >> $A/auto.log 2>&1 || { echo FAIL post_kit rc=$? >> $A/auto.log; exit 24; }
echo AUTO_DONE >> $A/auto.log

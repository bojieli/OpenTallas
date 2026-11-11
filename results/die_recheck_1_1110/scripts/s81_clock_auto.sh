#!/bin/bash
# DIE-RECHECK-1 (ADVISORY, DO_NOT_COUNT): automatic S81 die clock + clock-only die route + related-pair die STA on a
# new S81 plan of record.  Run by die_recheck_cron.sh through ot-run on epyc8 when the S81 plan sha changes.
#   s81_clock_auto.sh REPO PLAN_REL SHA   (REPO = the watch checkout; plan + tools are snapshotted into s81/auto/SHA)
# Form: the balanced min-depth feed (feed_bal.py, regenerated on the plan) + one region per partition + region DME,
# the DS85 r470 recipe (s81/cfg/s81_recheck_bal.yaml as template).  Writes s81/auto/SHA/clock_summary.json.
set -uo pipefail
cd /
W=/srv/opentallas-scratch2/claude/die-recheck-1
SRC=$1; PREL=$2; SHA=$3
A=$W/s81/auto/$SHA; mkdir -p $A
# snapshot (the watch checkout moves on the next plan event while this runs); the kit reads repo data via relative paths
REPO=$A/repo; rm -rf $REPO; mkdir -p $REPO/physical
cp -a $SRC/tools $SRC/data $REPO/ 2>/dev/null; cp -a $SRC/physical/asap7_memory_macros $REPO/physical/ 2>/dev/null
rsync -a --exclude=/hbm --exclude=/hbm_arch --exclude=/hbm_arch_cores --exclude="/qwen_*" --exclude=/s81_head $SRC/physical/die_plan/ $REPO/physical/die_plan/
PLAN=$REPO/$PREL; TOOLS=$REPO/tools/die_plan
echo "auto $SHA plan $PLAN repo $REPO $(date)" > $A/auto.log
python3 -I - "$PLAN" "$A/map.json" <<'EOF' >> $A/auto.log 2>&1 || { echo FAIL map >> $A/auto.log; exit 21; }
import gzip, json, sys
p = sys.argv[1]; d = json.load(gzip.open(p) if p.endswith('.gz') else open(p))
json.dump({'part_region': {x['name']: x['name'] for x in d['partitions']}}, open(sys.argv[2], 'w'))
print('regions', len(d['partitions']))
EOF
sed -e "s#^  plan: .*#  plan: $PLAN#" -e "s#^  region_map: .*#  region_map: $A/map.json#" -e "s#^  feed: .*#  feed: $A/feed_bal.json#" \
  $W/s81/cfg/s81_recheck_bal.yaml > $A/kit.yaml
V=auto_$SHA
AVOID=""
for try in 1 2 3 4; do
  python3 -s $W/scripts/feed_bal.py $PLAN $TOOLS $A/feed_bal.json --avoid "$AVOID" --phy-parents $W/s81/cfg/feed_sb6_h2_2249.json >> $A/auto.log 2>&1 || { echo FAIL feed >> $A/auto.log; exit 22; }
  rm -rf $W/s81/ck_$V
  python3 -s $REPO/tools/clk/ot_clk.py kit $A/kit.yaml --out $W/s81/ck_$V --workers 24 > $A/kit.log 2>&1 && break
  # a feed leg with no legal repeater site within reach: drop that feed edge and rebuild (nearest feed tap to the leg end)
  E=$(python3 -I $W/scripts/reach_edge.py $A/kit.log $A/feed_bal.json)
  [ -n "$E" ] || { echo "FAIL kit (try $try, not a feed-leg reach failure)" >> $A/auto.log; exit 23; }
  echo "kit try $try: reach failure on feed edge $E -> avoid" >> $A/auto.log
  AVOID="${AVOID:+$AVOID,}$E"
  [ $try = 4 ] && { echo FAIL kit after 4 tries >> $A/auto.log; exit 23; }
done
echo "kit ok, avoid=[$AVOID]" >> $A/auto.log
PLAN=$PLAN TOOLS=$TOOLS AUTO=1 $W/scripts/post_kit.sh $V >> $A/auto.log 2>&1 || { echo FAIL post_kit rc=$? >> $A/auto.log; }
python3 -I - "$A" "$W/s81/sta_$V.log" "$W/s81/out_$V/metrics.json" "$W/s81/ck_$V/kit.log" "$SHA" <<'EOF' >> $A/auto.log 2>&1
import json, re, sys
from pathlib import Path
A, sta, met, kit, sha = sys.argv[1:6]
s = dict(sha=sha, sta={}, metrics=None)
if Path(sta).exists():
    for ln in Path(sta).read_text().splitlines():
        m = re.match(r'\S+ (TT|FF) (intra|landed)\s+pairs (\d+) setup\s+(\S+) \(neg (\d+)\) hold\s+(\S+) \(neg (\d+)\) skew\s+(\S+)', ln)
        if m:
            c, k = m.group(1), m.group(2)
            r = dict(pairs=int(m.group(3)), setup=float(m.group(4)), setup_neg=int(m.group(5)), hold=float(m.group(6)),
                     hold_neg=int(m.group(7)), skew=float(m.group(8)))
            kc = re.search(r'kit-contract hold (\S+) \(W (\S+), need (\S+), neg (\d+)\)', ln)
            if kc:
                r['kit_contract'] = dict(hold=float(kc.group(1)), window=float(kc.group(2)), need=float(kc.group(3)), neg=int(kc.group(4)))
            lw = re.search(r"'damage_max_ps': (\S+), 'verdict': '(\w+)'", ln)
            if lw:
                r['landing'] = dict(damage_max=float(lw.group(1).rstrip(',')), verdict=lw.group(2))
            s['sta'][c + '_' + k] = r
if Path(met).exists():
    M = json.loads(Path(met).read_text())
    s['metrics'] = {c: {k: v[k] for k in ('tap_arr_min', 'tap_arr_max', 'unshared_stages_max', 'window_need_max',
                                          'structural_over', 'wrapped_clear_below0')} for c, v in M['corners'].items()}
    s['lps_wrapped'] = M.get('lps_wrapped')
s['kit_done'] = 'stage done' in Path(kit).read_text() if Path(kit).exists() else False
Path(A, 'clock_summary.json').write_text(json.dumps(s, indent=1))
print('SUMMARY', json.dumps(s))
EOF
echo AUTO_DONE >> $A/auto.log

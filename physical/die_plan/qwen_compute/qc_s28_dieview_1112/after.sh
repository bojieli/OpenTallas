#!/bin/bash
# QC-S28-DIEVIEW: full AFTER pipeline on any QC plan, driven from localhost.
#   after.sh HOST:/abs/plan.json TAG [HOST:/abs/src_tree_with_new_files]
# 1. copy the plan into the epyc9 hardlinked view tree (new name, nothing overwritten); missing referenced files are
#    pulled from the given lane tree (new files only)
# 2. epyc9: route_supply + die_hop_scan + qc_die_audit (run_view.sh), compare vs the s28 before audit
# 3. epyc4: render (nice 19); PNGs + tables to the local scratchpad and epyc8 shared dir
set -u
SRC=$1; TAG=$2; TREE=${3:-}
SSH="timeout 900 ssh -n -o ControlPath=none"
W=/srv/opentallas-scratch2/claude/qc-s28-dieview
V=$W/srcview
D=/srv/opentallas-scratch3/claude/qc-s28-dieview
LOC=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/coreplace/qc-s28-dieview/$TAG
mkdir -p $LOC
H=${SRC%%:*}; P=${SRC#*:}
NAME=plan_dv_$TAG.json
if [ "$H" = epyc9 ]; then $SSH epyc9 "cp $P $V/physical/die_plan/qwen_compute/plan_of_record/$NAME"
else $SSH $H "timeout 300 scp -q -o ControlPath=none $P epyc9:$V/physical/die_plan/qwen_compute/plan_of_record/$NAME"; fi
if [ -n "$TREE" ]; then
  TH=${TREE%%:*}; TP=${TREE#*:}
  MISS=$($SSH epyc9 "cd $V && python3 -I -c \"
import json,os
p=json.load(open('physical/die_plan/qwen_compute/plan_of_record/$NAME'))
m=set()
def w(o):
  if isinstance(o,dict): [w(v) for v in o.values()]
  elif isinstance(o,list): [w(v) for v in o]
  elif isinstance(o,str) and o.startswith('physical/') and len(o)<300 and ' ' not in o and not os.path.exists(o): m.add(o)
w(p['partition_types']); w(p.get('clock',{})); w(p.get('budgets',{}))
print(' '.join(sorted(m)))\"")
  echo "missing in view tree: $(echo $MISS | wc -w)"
  for f in $MISS; do
    $SSH epyc9 "mkdir -p $V/$(dirname $f)"
    if [ "$TH" = epyc9 ]; then $SSH epyc9 "[ -e $V/$f ] || cp $TP/$f $V/$f"
    else $SSH $TH "[ -e $TP/$f ] && timeout 120 scp -q -o ControlPath=none $TP/$f epyc9:$V/$f"; fi
  done
fi
$SSH epyc9 "bash $W/run_view.sh $NAME $TAG && python3 -I $W/qc_die_compare.py $W/audit_before/audit.tsv $W/out_$TAG/audit/audit.tsv $W/out_$TAG/compare.tsv > $W/out_$TAG/compare.txt; head -3 $W/out_$TAG/compare.txt; grep -h 'overlaps' $W/out_$TAG/audit.stdout"
timeout 300 scp -q -o ControlPath=none epyc9:$W/out_$TAG/audit/audit.json.gz epyc9:$W/out_$TAG/audit/audit.tsv epyc9:$W/out_$TAG/compare.tsv epyc9:$W/out_$TAG/compare.txt epyc9:$W/out_$TAG/hops.json $LOC/
timeout 300 scp -q -o ControlPath=none $LOC/audit.json.gz epyc4:$D/audit_$TAG.json.gz
$SSH epyc4 "cd $D && gunzip -f audit_$TAG.json.gz && nice -n 19 python3 -P -E qc_die_render.py audit_$TAG.json render_$TAG --tag $TAG --title '$TAG $(basename $P)' | tail -1"
timeout 300 scp -q -o ControlPath=none "epyc4:$D/render_$TAG/*.png" $LOC/
$SSH epyc8 "mkdir -p /srv/opentallas-scratch2/claude/qc-s28-dieview/$TAG" && timeout 300 scp -q -o ControlPath=none $LOC/*.png $LOC/*.tsv $LOC/compare.txt epyc8:/srv/opentallas-scratch2/claude/qc-s28-dieview/$TAG/
echo "AFTER $TAG done -> $LOC"

#!/bin/bash
# DIE-KV-25: DIE-KV-22 post.sh proof steps only (no refit/bind): tap arrivals TT/FF -> mesh/droop regions -> fall merge
set -u; T=$1; O=/srv/opentallas-scratch2/claude/die-kv-25-1029; cd $O
S=/srv/opentallas-scratch2/claude/wt/die-kv-25/tools/die_plan; LK=/srv/opentallas-scratch2/claude/land-kv-1027; L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128
P=$O/proof_$T; PT=$O/proofT_$T; PF=$O/proofF_$T; mkdir -p $P
for C in TT FF; do python3 $LK/trial_tap_arrivals.py clk_$T/tree.json out_${T}_$C/arr_$C.txt $C $P/tap_arrivals_$C.json || exit 1; done
python3 - clk_$T/tree.json $L/land128_regions.json $P <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-25: tap table only (no mesh)", taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
python3 $S/tap_fall_merge.py $P TT out_${T}_TT/duty_TT.txt --out $PT || exit 1
python3 $S/tap_fall_merge.py $PT FF out_${T}_FF/duty_FF.txt --out $PF || exit 1
echo PROOF_DONE $(date)

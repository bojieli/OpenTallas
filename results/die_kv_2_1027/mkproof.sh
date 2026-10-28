#!/bin/bash
# DIE-KV-2: die_sta_related PROOF dir from a die_trial combo GRT (LAND-KV-1/2 recipe: trial_tap_arrivals.py + tap table + droop regions = clock regions)
# mkproof.sh TAG REGIONS_JSON PLAN
E=/srv/opentallas-scratch2/claude/die-kv-2-1027; T=$1; RG=$2; PL=$3
mkdir -p $E/proof$T
for C in TT FF; do python3 /srv/opentallas-scratch2/claude/land-kv-1027/trial_tap_arrivals.py $E/clk$T/tree.json $E/out${T}_$C/arr_$C.txt $C $E/proof$T/tap_arrivals_$C.json; done
python3 - $E/clk$T/tree.json $RG $E/proof$T <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-2: tap table only (no mesh); die_trial link_fishbone region trees",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
python3 $E/src/tools/die_plan/die_sta_related.py $E/proof$T --plan $PL --out $E/sta$T --cppr-lca --clock-ocv table --clock-droop shared --droop-regions $E/proof$T/droop_regions.json --hold-buffers HB4 --landing-window-ps 416.5 > $E/sta$T.log 2>&1
echo STA_RC $? >> $E/sta$T.log

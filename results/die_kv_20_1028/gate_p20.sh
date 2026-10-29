#!/bin/bash
# DIE-KV-20: re-padded phy taps (pad_kv20_pad.json) -> proof (DIE-KV-15 ca.sh recipe) -> fall merge (FLOW-ONEMODEL-1) ->
# main die_sta_related (main 6a56d5811 tools) on the EXISTING count-aligned bind st_fall_bind_parts (CA verify on the new tree)
# + the 3 signed KV views (gate_views.sh), clock-cal spice (record comparison) and spice_edge (NUMBER-CHECK-INV-1 gate number).
# The DIE-KV-15 record proofF_fb is re-run with the same tools for an apples-to-apples baseline.
set -u
O=/srv/opentallas-scratch2/claude/die-kv-20-1028; R=/srv/opentallas-scratch2/claude/die-kv-15-1028; T=p20
S=$O/main_6a56d5811/tools/die_plan; LK=/srv/opentallas-scratch2/claude/land-kv-1027; L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128
PL=$R/hm_r26q15c.json; V=/srv/opentallas-scratch2/claude/die-kv-19-1028/views; cd $O
P=$O/proof_$T; PT=$O/proofT_$T; PF=$O/proofF_$T; mkdir -p $P
for C in TT FF; do python3 $LK/trial_tap_arrivals.py clk_$T/tree.json out_${T}_$C/arr_$C.txt $C $P/tap_arrivals_$C.json || exit 1; done
python3 - clk_$T/tree.json $L/land128_regions.json $P <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-20: tap table only (no mesh); DIE-KV-15 fishbone tree + re-derived phy pads",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
python3 $S/tap_fall_merge.py $P TT out_${T}_TT/duty_TT.txt --out $PT || exit 1
python3 $S/tap_fall_merge.py $PT FF out_${T}_FF/duty_FF.txt --out $PF || exit 1
ls $PF
CV=""; for d in $V/*/view/*; do CV="$CV --core-view $(basename $d)=$d"; done
run() { # name proof cal
  mkdir -p $O/sta_$1; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $O/sta_$1/ 2>/dev/null
  python3 $S/die_sta_related.py $2 --plan $PL --out $O/sta_$1 --clock-cal $3 --cppr-lca \
    --count-align $R/ca_fb_inv_r150/st_fall_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared \
    --droop-regions $2/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv $CV --core-insertion view \
    > $O/sta_$1.log 2>&1; echo STA_$1_RC $?; }
run p20_spice $PF spice & run p20_edge $PF spice_edge & run rec_spice $R/proofF_fb spice & run rec_edge $R/proofF_fb spice_edge & wait
echo GATE_DONE $(date)

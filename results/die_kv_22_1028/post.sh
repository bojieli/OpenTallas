#!/bin/bash
# DIE-KV-22 post-GRT on tree T: own-leg refit (convergence check) -> proof (DIE-KV-21 gate3.sh recipe) -> count-align re-bind
# (bind.sh, record recipe, --start-prev record) -> gate (spice_edge = gate number, spice = record comparison).
set -u; T=$1; O=/srv/opentallas-scratch2/claude/die-kv-22-1028; cd $O
S=/srv/opentallas-scratch2/claude/die-kv-20-1028/main_6a56d5811/tools/die_plan; LK=/srv/opentallas-scratch2/claude/land-kv-1027; L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128
REC=/srv/opentallas-scratch2/claude/die-kv-15-1028/ca_fb_inv_r150/st_fall_bind_parts.json
python3 /srv/opentallas-scratch2/claude/die-kv-21-1028/main/tools/die_plan/fit_dme_stage_cal.py --tree kit_$T/clock/tree.json --arr-prefix out_$T \
  --tap-from kv_cal_fit_c.json --rep-um 150 --built-with ${BUILT:-kv_cal_fit_c.json} -o kv_cal_fit_$T.json > fit_$T.log 2>&1; echo FIT_RC $?
P=$O/proof_$T; PT=$O/proofT_$T; PF=$O/proofF_$T; mkdir -p $P
for C in TT FF; do python3 $LK/trial_tap_arrivals.py clk_$T/tree.json out_${T}_$C/arr_$C.txt $C $P/tap_arrivals_$C.json || exit 1; done
python3 - clk_$T/tree.json $L/land128_regions.json $P <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-22: tap table only (no mesh); all-region DME delay trees on the KV-21 fitted stage model",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
python3 $S/tap_fall_merge.py $P TT out_${T}_TT/duty_TT.txt --out $PT || exit 1
python3 $S/tap_fall_merge.py $PT FF out_${T}_FF/duty_FF.txt --out $PF || exit 1
./bind.sh $T $PF --start-prev $REC
./gate.sh ${T}_rec_edge $PF $REC spice_edge & ./gate.sh ${T}_edge $PF $O/st_${T}_bind_parts.json spice_edge & ./gate.sh ${T}_spice $PF $O/st_${T}_bind_parts.json spice & wait
echo POST_DONE $(date)

#!/bin/bash
# QW-G5STA 10-20 run-dir setup (fleet, ep6): successor of dv2f20g5 = g5 source d502ea9ae + 915e95212 slice landing channels
# (OT_SPLIT_DV -> dv2r8f7r_qdv_p2462_xg864.json, OT_SPLIT_LAND_LIST_IN_FACE='', core feed x +5 G = 17280).
# usage: setup.sh TAG PLANMODE   PLANMODE = self (g5's own re-derived land plan, E rows only) | bi (the g5 bi plan, as g5)
set -eu
T=${1:?tag}; PM=${2:?self|bi}; R=/srv/opentallas-scratch/claude/mu-die-qw; G5=$R/dv2f20g5; S=$R/$T; K=$R/qw-g5sta-kit
[ -e $S ] && { echo "$S exists"; exit 3; }
mkdir -p $S
cp -a $G5/src $S/src
cp $K/dv_xgap_plan.py $S/src/tools/qwen_split/
cp $K/dv2r8f7r_qdv_p2462_xg864.json $S/src/results/arch/qwen_split_compute_1014/dieplan2_1016/
cp $K/qwen_rom_fulldie_b3r2.py $S/src/tools/
echo "b3e959583 (QW-G5STA: d502ea9ae + slice landing channels xg864 915e95212 + E/W landing frames b3e959583; run $T plan=$PM)" > $S/src/SOURCE_COMMIT
for f in gen.sh run.sh pre.sh chain.sh reset_release_prior_g4try3.json reset_release_prior_g4try3.sha256 land_plan_bi_chain.json; do cp $G5/$f $S/; done
sed -i "s#/mu-die-qw/dv2f20g5\b#/mu-die-qw/$T#g; s#dv2f20g5-qwgen5#$T-qwg5sta#g" $S/gen.sh $S/run.sh $S/pre.sh $S/chain.sh
sed -i 's#dv2r8f7r_qdv_p2462\.json#dv2r8f7r_qdv_p2462_xg864.json#' $S/run.sh
grep -q dv2r8f7r_qdv_p2462_xg864.json $S/run.sh || { echo "run.sh dv plan not switched"; exit 4; }
sed -i "s#chain_after_build.sh dv2f20g5 #chain_after_build.sh $T #" $S/chain.sh; grep -q "chain_after_build.sh $T " $S/chain.sh || { echo "chain tag not switched"; exit 4; }
ln -sfn $S /srv/opentallas-scratch/claude/qwen-split-compute/$T
# GEN env of this successor (gen.sh -> run.sh knobs)
sed -i "2i export IN_FACE= CORE_FEED_XY=17280.0,12096.0 OT_SPLIT_FWD_LAND_EW_MASTERS=qfd_dv_slice2   # QW-G5STA: land slice<->slice rows at die level; core feed stays in the W0|E0 seam (+5 x 86.4)" $S/gen.sh
if [ "$PM" = self ]; then
  python3 - $G5/chain/land_plan.json $S/land_plan_g5self.json <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); rows = [r for r in p['links'] if r.get('E') is not None]
hist = {}
for r in rows: hist[str(r['E'])] = hist.get(str(r['E']), 0) + 1
p['links'] = rows
p['summary'] = dict(links=len(rows), E_hist=hist, window_fail=[r['bid'] for r in rows if not r.get('window_ok')], no_slack=[],
                    dropped_no_slack=p['summary'].get('no_slack', []), source='dv2f20g5 chain/land_plan.json (g5 own STA), E rows only')
json.dump(p, open(sys.argv[2], 'w'), indent=1); print(json.dumps(p['summary']))
PY
  sed -i "s#^LP=.*#LP=\$S/land_plan_g5self.json#" $S/gen.sh
fi
grep -n -E "^LP=|^export IN_FACE|xg864" $S/gen.sh $S/run.sh | cut -c1-200
cp $K/follow.sh $K/phase2_fleet.sh $K/phase3.sh $S/
echo "$(date '+%F %T %Z') QW-G5STA setup done ($T plan=$PM)" >> $S/PILOT.log

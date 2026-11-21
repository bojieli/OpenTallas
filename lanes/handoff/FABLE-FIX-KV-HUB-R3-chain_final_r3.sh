#!/bin/bash
# FABLE-FIX-KV-HUB-R3: tree_h final plan = chain plan_p3 + ring row fields (views, pins, reset_net) + hub_Wo stage-0 row; then G0.
set -euo pipefail
W=/srv/opentallas-scratch2/claude/fable-fix-kv-hub; T=$W/tree_h; L=$W/launch_h; O=$W/hub_d28_r3; R=$W/r3
D=physical/die_plan/qwen_kvsys; P=$D/plan_of_record; VREL=$D/kvd28_hubring_views
export PYTHONDONTWRITEBYTECODE=1 OT_HCPARAM_ALL=1 OT_KV_HEAD_KST=2 TMPDIR=$O/tmp
test $(sha256sum $T/$P/plan_c.json | cut -c1-12) = cb6b8d5286c4
test $(ls $R/views/kv_*/clock_contract.json $R/views/kv_*/landing_evidence/manifest.json | wc -l) = 10
if [ ! -e $T/$VREL ]; then
  chmod u+w $T/$D; mkdir -p $T/$VREL.tmp
  for m in $(ls $R/rk); do [ -e $T/$VREL.tmp/$m ] || cp -a $R/views/$m $T/$VREL.tmp/$m; done
  cp -p $R/views/SHA256SUMS $T/$VREL.tmp/; mv $T/$VREL.tmp $T/$VREL
fi
chmod u+w $T/$P/cores/kv_ring
for m in $(ls $R/rk); do f=$T/$P/cores/kv_ring/${m}_pins.json; [ -e $f ] || { cp -p $R/rk/$m/pins.json $f.r3 && mv $f.r3 $f; }; done
cd $L
ls $VREL | head -8; ls $P/cores/kv_ring | grep -c -E "86ca8|ebc75|abd47|6081a|aee53"
python3 -I -B $R/compose.py $O/plans/plan_p3.json $O/plans/plan_p4.json $VREL $R/rows_final_d28.json > $R/compose.log
cp -p $O/plans/plan_p4.json $T/$P/plan_c.json.ffkh && mv $T/$P/plan_c.json.ffkh $T/$P/plan_c.json
echo FINAL_PLAN $(sha256sum $T/$P/plan_c.json | cut -c1-12)
bash /srv/opentallas-scratch2/claude/kv-plan-r3/d27c/gate_g0_d26.sh $L $O/g0gate_p4 || true
tail -3 $O/g0gate_p4/gate.out | cut -c1-500
echo FINAL_R3_DONE

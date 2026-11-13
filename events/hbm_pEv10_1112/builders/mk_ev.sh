#!/bin/bash
# DIE-HBM-101 event parts on a base plan: mk_ev.sh BASE OUT   (plans/<name> under hp1lane)
set -e; H=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane; P=$H/plans; K=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18
B=$1; O=$2; cd $H
for d in $O.w0 $O.w1 $O.w2 $O.w3 $O; do rm -rf $P/$d; cp -a $P/$B $P/$d; done
R="q_hub_nw:L1239x1=1,q_hub_ne:L5040x1=1,q_hub_nw:L1219x1=2,q_hub_ne:L5019x1=2,q_hub_nw:L1218x1=3,q_hub_ne:L5018x1=3,q_hub_nw:L1225x1=4,q_hub_ne:L5025x1=4,q_hub_nw:L1238x1=5,q_hub_ne:L5039x1=5"
L=q_hub_nw:L1218x1,q_hub_nw:L1219x1,q_hub_nw:L1225x1,q_hub_nw:L1238x1,q_hub_nw:L1239x1,q_hub_ne:L5018x1,q_hub_ne:L5019x1,q_hub_ne:L5025x1,q_hub_ne:L5039x1,q_hub_ne:L5040x1
TOP="NW_su00:L8300x4=3,NW_su00:L1254x2=5,NE_su00:L8300mx4=3,NE_su00:L5076x4=4,NW_b113:L8350x3=3,NW_b113:L1271x7=4,NE_b113:L8350mx3=3,NW_b113:L8300x3=r,NW_b112:L8350x1=r,NE_b112:L8350mx1=r"
SPL=NW_su00:L8300x4,NW_su00:L1254x2,NE_su00:L8300mx4,NE_su00:L5076x4,NW_b113:L8350x3,NW_b113:L1271x7,NE_b113:L8350mx3,NW_b113:L8300x3,NW_b112:L8350x1,NE_b112:L8350mx1
python3 -I hbm101/hp5_rows.py $P/$B/die_plan.json $P/$O.w0/die_plan.json $R >/dev/null
python3 -I hbm101/hp5_s1.py $P/$O.w0/die_plan.json $P/$O.w1/die_plan.json $L >/dev/null
python3 -I hbm101/hp5_sp.py $P/$O.w1/die_plan.json $P/$O.w2/die_plan.json $L >/dev/null
python3 -I hbm101/hp5_top.py $P/$O.w2/die_plan.json $P/$O.w3/die_plan.json "$TOP" | grep -c respace
cp $P/$O.w3/die_plan.json $P/$O/in.json
for k in 1 2 3 4; do
  (cd $K; python3 -I tools/die_plan/ft_nudge.py $P/$O/in.json $P/$O/die_plan.json $P/$O/nudge_ledger_$k.json 2>&1 | tail -n 1)
  n=$(python3 -I hbm101/hop_split.py $P/$O/die_plan.json $P/$O/in.json $SPL | tail -n 1 | awk '{print $2}')
  echo "round $k inserted $n"; [ "$n" = "0" ] && break
done
rm -f $P/$O/in.json
(cd $K; python3 -I tools/die_plan/gen.py latency $P/$O/die_plan.json --inplace 2>&1 | tail -n 1 | cut -c1-40)
sha256sum $P/$O/die_plan.json | cut -c1-12
for d in $O.w0 $O.w1 $O.w2 $O.w3; do rm -rf $P/$d; done
sed s/hp5a/$O/g $H/hbm101/g0_hp5a.sh > $H/hbm101/g0_$O.sh

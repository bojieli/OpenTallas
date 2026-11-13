#!/bin/bash
# pEv6 = pEv4f + q_sm0 family symmetry (bindEv4 R8_STRAP_PAD + TYPE_SPLIT q_sm0):
#   L8300m 24->27 (=L8300), L8350 20->22 (=L8350m), L8313/L8313m 11->13 => u_qs_c_land pads 0/5/14 both sides (cap 15)
set -e
H=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane; cd $H
K=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18; P=$H/plans; O=pEv6
rm -rf $P/$O; cp -a $P/pEv4f $P/$O
python3 -I hbm101/add_mid.py $P/$O/die_plan.json $P/$O/die_plan.json q_su00:L8300mx4 3
i=0
for s in q_spu0:L8350x2=L8350 q_spu0:L8350x2=L8350 q_su00__physical_v1:L8313x2=L8313 q_su00__physical_v1:L8313x2=L8313 q_su00:L8313mx2=L8313m q_su00:L8313mx2=L8313m; do
  i=$((i+1)); (cd $K; python3 -I tools/die_plan/ft_add_station.py $P/$O/die_plan.json $P/$O/t.json $P/$O/add_station_$i.json ${s%=*} ${s#*=} 2>&1 | tail -n 1 | cut -c1-160); mv $P/$O/t.json $P/$O/die_plan.json
done
cp $P/$O/die_plan.json $P/$O/in.json; (cd $K; python3 -I tools/die_plan/ft_nudge.py $P/$O/in.json $P/$O/die_plan.json $P/$O/nudge_ledger_ev6.json 2>&1 | tail -n 1); rm -f $P/$O/in.json
(cd $K; python3 -I tools/die_plan/gen.py latency $P/$O/die_plan.json --inplace 2>&1 | tail -n 1 | cut -c1-80)
sha256sum $P/$O/die_plan.json | cut -c1-12
python3 -I hbm101/fam.py L8300,L8300m,L8350,L8350m,L8313,L8313m $O
python3 -I hbm101/latcheck.py $P/$O/die_plan.json /srv/opentallas-scratch2/claude/die-layout-hbm/bindEv4/asbuilt.json
python3 -I hbm101/pairsym.py $P/$O/die_plan.json
bash hbm101/g0_pEv6.sh
echo "pEv6 done"

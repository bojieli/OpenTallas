#!/bin/bash
# pEv9 = pEv8 (LATCHECK-1 pricing) + q_sm0 as-built symmetry: NW L8300 42 -> 49 (= L8300m; hub kit chains 15 vs 22)
#   so NW/NE q_sm0 landing pads are equal (fixed dly, no strap site / cap)
set -e
H=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane; cd $H
K=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18; P=$H/plans; O=pEv9
rm -rf $P/$O; cp -a $P/pEv8 $P/$O
python3 -I hbm101/add_mid.py $P/$O/die_plan.json $P/$O/die_plan.json q_b001__physical_v1:L28y2 3
python3 -I hbm101/add_mid.py $P/$O/die_plan.json $P/$O/die_plan.json q_b113:L8300x3 2
python3 -I hbm101/add_mid.py $P/$O/die_plan.json $P/$O/die_plan.json q_su00__physical_v1:L8300x4 2
cp $P/$O/die_plan.json $P/$O/in.json; (cd $K; python3 -I tools/die_plan/ft_nudge.py $P/$O/in.json $P/$O/die_plan.json $P/$O/nudge_ledger_ev9.json 2>&1 | tail -n 1); rm -f $P/$O/in.json
(cd $K; python3 -I tools/die_plan/gen.py latency $P/$O/die_plan.json --inplace 2>&1 | tail -n 1 | cut -c1-80)
sha256sum $P/$O/die_plan.json | cut -c1-12
python3 -I -c "import json;t=json.load(open(\"$P/$O/die_plan.json\"))[\"latency\"][\"lanes\"];print({k:t[k][\"cycles\"] for k in (\"L8300\",\"L8300m\",\"L8350\",\"L8350m\",\"L8313\",\"L8313m\")})"
python3 -I hbm101/latcheck.py $P/$O/die_plan.json /srv/opentallas-scratch2/claude/die-layout-hbm/bindEv6/asbuilt.json
python3 -I hbm101/pairsym.py $P/$O/die_plan.json
bash hbm101/g0_pEv9.sh
echo "pEv9 done"

#!/bin/bash
# pEv10 = pEv9 + q_sm1 as-built symmetry: NW L8301 28 -> 29 (= L8301m), bindEv8 R8_STRAP_PAD q_sm1 pad 19 / TYPE_SPLIT q_sm1
set -e
H=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane; cd $H
K=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18; P=$H/plans; O=pEv10
rm -rf $P/$O; cp -a $P/pEv9 $P/$O
python3 -I hbm101/add_mid.py $P/$O/die_plan.json $P/$O/die_plan.json q_su11__physical_v1:L8301x1 1
cp $P/$O/die_plan.json $P/$O/in.json; (cd $K; python3 -I tools/die_plan/ft_nudge.py $P/$O/in.json $P/$O/die_plan.json $P/$O/nudge_ledger_ev10.json 2>&1 | tail -n 1); rm -f $P/$O/in.json
(cd $K; python3 -I tools/die_plan/gen.py latency $P/$O/die_plan.json --inplace 2>&1 | tail -n 1 | cut -c1-80)
sha256sum $P/$O/die_plan.json | cut -c1-12
python3 -I -c "import json;t=json.load(open(\"$P/$O/die_plan.json\"))[\"latency\"][\"lanes\"];print({k:t[k][\"cycles\"] for k in (\"L8300\",\"L8300m\",\"L8301\",\"L8301m\",\"L8313\",\"L8313m\")})"
python3 -I hbm101/latcheck.py $P/$O/die_plan.json /srv/opentallas-scratch2/claude/die-layout-hbm/bindEv6/asbuilt.json
python3 -I hbm101/pairsym.py $P/$O/die_plan.json
bash hbm101/g0_pEv10.sh
echo "pEv10 done"

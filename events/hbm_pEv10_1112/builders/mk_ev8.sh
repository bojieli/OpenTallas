#!/bin/bash
# pEv8 = pEv6 + LATCHECK-1 fixed_cycles pricing of 118 UNPRICED_KIT_STATIONS lanes (bindEv6 as-built CLI)
set -e
H=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane; cd $H
K=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18; P=$H/plans; O=pEv8
rm -rf $P/$O; cp -a $P/pEv6 $P/$O
python3 -I hbm101/fcfix.py $P/pEv6/die_plan.json $P/$O/die_plan.json hbm101/asb/ev6.tsv
(cd $K; python3 -I tools/die_plan/gen.py latency $P/$O/die_plan.json --inplace 2>&1 | tail -n 1 | cut -c1-80)
sha256sum $P/$O/die_plan.json | cut -c1-12
python3 -I hbm101/latcheck.py $P/$O/die_plan.json /srv/opentallas-scratch2/claude/die-layout-hbm/bindEv6/asbuilt.json
python3 -I hbm101/pairsym.py $P/$O/die_plan.json
bash hbm101/g0_pEv8.sh
echo "pEv8 done"

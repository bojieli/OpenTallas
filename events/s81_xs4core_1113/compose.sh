#!/bin/bash
# XS4-CORE plan chain: base -> delta (e1) -> reach_fix (e2) -> collector publish (e3) -> station table refresh (e4) -> G0 + G0C
cd /srv/opentallas-scratch2/claude/wt/hard-s81-dsdv-1; export PYTHONDONTWRITEBYTECODE=1
PWD_RS=/srv/opentallas-scratch2/claude/hard-s81-dsdv-1/rs_tool; P=physical/die_plan/s81; ST=/srv/opentallas-scratch2/claude/hard-s81-dsdv-1/chain6.status; : > $ST
python3 -I -B $P/delta_xs4_core_1113.py $P/plan_xs4_base.json $P/plan_xs4_m1.json --report /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m1_report.json > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m1.log 2>&1; r=$?; echo DELTA_RC=$r >> $ST; [ $r = 0 ] || exit 1
nice -n 5 python3 -I -B tools/die_plan/reach_fix.py fix $P/plan_xs4_m1.json --repo . --types 'dsdv_slice_\w+_C__t\d+$' --classes 1,2,3,4,5 -j 16 --out-plan $P/plan_xs4_m2.json --event /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m2_reach_event.json > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m2.log 2>&1; r=$?; echo REACH_RC=$r >> $ST; [ $r = 0 ] || exit 1
python3 -I -B $P/delta_xs4_collector_1113.py $P/plan_xs4_m2.json $P/plan_xs4_m3.json events/s81_ready12bA_1112/landed_sidecar_h2_psplit_all.sync.json.gz /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/landed_sidecar_h2_psplit_all.xs4m.json > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m3.log 2>&1; r=$?; echo COLL_RC=$r >> $ST; [ $r = 0 ] || exit 1
python3 -I -B tools/die_plan/stage_kit_source_table_refresh.py $P/plan_xs4_m3.json /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/asbuilt_xs4.json $P/plan_xs4_m3a.json /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g4a_ksrc.json > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m4.log 2>&1; r=$?; echo KSRC_RC=$r >> $ST; [ $r = 0 ] || exit 1
python3 -I -B tools/die_plan/stage_kit_source_table_refresh.py $P/plan_xs4_m3a.json /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/asbuilt_xs4.json $P/plan_xs4_m4.json /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m4_kdst.json --dest >> /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/m4.log 2>&1; r=$?; echo KDST_RC=$r >> $ST; [ $r = 0 ] || exit 1
sha256sum $P/plan_xs4_m4.json | cut -c1-12 >> $ST
mkdir -p /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0_m4 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0c_m4 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0base_m; (nice -n 5 python3 -I -B tools/die_plan/check.py $P/plan_xs4_base.json --out /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0base_m --quiet > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0base_m.log 2>&1; echo G0BASE_RC=$? >> $ST) &
nice -n 5 python3 -I tools/die_plan/street_rule.py check $P/plan_xs4_m4.json --repo . --match "dsdv_slice_\w+_C__t\d+$" --out /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/rstreet/chk_m4.json > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/rstreet/chk_m4.log 2>&1; echo RS_RC=$? >> $ST
nice -n 5 python3 -I -B tools/die_plan/check.py $P/plan_xs4_m4.json --out /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0_m4 --quiet > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0_m4.log 2>&1; echo G0_RC=$? >> $ST
nice -n 5 python3 -I -B tools/die_plan/check.py $P/plan_xs4_m4.json --out /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0c_m4 --quiet --completeness > /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/g0c_m4.log 2>&1; echo G0C_RC=$? >> $ST
echo DONE >> $ST
wait
echo ALLDONE >> $ST

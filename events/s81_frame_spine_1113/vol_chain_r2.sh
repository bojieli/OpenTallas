#!/bin/bash
# FRAME-SPINE-1113 chain (FRAME-FORMS-1-VOL): plan_fin -> c0b added_tap_legalize (kit tap legality, move only) -> c1 added_tap_recentre (no add) -> c2 collector publish
# (plan + psplit_all + gear sidecars) -> c3a kit source table refresh -> c3 --dest -> plan_frame_spine_<sha12>.json   (cwd = worktree)
bash /srv/opentallas-scratch3/claude/frame-forms-1/all1/compose_r2.sh || exit 7
set -u; cd /srv/opentallas-scratch3/claude/wt/frame-forms-1 || exit 9; export PYTHONDONTWRITEBYTECODE=1
V=/srv/opentallas-scratch3/claude/frame-forms-1/vol; A=/srv/opentallas-scratch3/claude/frame-forms-1/all1; E=events/s81_frame_spine_1113; R=events/s81_ready12bA_1112
P=physical/die_plan/s81; ST=$V/chain_r2.status; : > $ST
AB=/srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/asbuilt_kitops1_7073a6b4a5.json
cp $A/plan_fin_r2.json $P/plan_ffr2_c0.json
python3 -I -B $E/added_tap_legalize.py $P/plan_ffr2_c0.json $P/plan_ffr2_c0b.json --types-file $A/accepted_r2.txt --parked $A/plan_A_tp.json --report $V/r2_c0b_legalize.json > $V/r2_c0b.log 2>&1; r=$?; echo LEGALIZE_RC=$r >> $ST; [ $r = 0 ] || exit 1
python3 -I -B tools/die_plan/added_tap_recentre.py $P/plan_ffr2_c0b.json --out $P/plan_ffr2_c1.json --types $(paste -sd, $A/accepted_r2.txt) --report $V/r2_c1_recentre.json > $V/r2_c1.log 2>&1; echo RECENTRE_RC=$? >> $ST
[ -s $P/plan_ffr2_c1.json ] || exit 2
python3 -I -B $E/delta_frame_collector_1113.py $P/plan_ffr2_c1.json $P/plan_ffr2_c2.json $A/accepted_r2.txt $V/r2_c2_collector.json \
  $R/landed_sidecar_h2_psplit_all.sync.json.gz $V/r2_side_psplit_all.c2.json $R/landed_sidecar_h2_psplit_all_gear.sync.json.gz $V/r2_side_psplit_all_gear.c2.json > $V/r2_c2.log 2>&1; r=$?; echo COLL_RC=$r >> $ST; [ $r = 0 ] || exit 1
python3 -I -B tools/die_plan/stage_kit_source_table_refresh.py $P/plan_ffr2_c2.json $AB $P/plan_ffr2_c3a.json $V/r2_c3a_ksrc.json > $V/r2_c3.log 2>&1; r=$?; echo KSRC_RC=$r >> $ST; [ $r = 0 ] || exit 1
python3 -I -B tools/die_plan/stage_kit_source_table_refresh.py $P/plan_ffr2_c3a.json $AB $P/plan_ffr2_c3.json $V/r2_c3_kdst.json --dest >> $V/r2_c3.log 2>&1; r=$?; echo KDST_RC=$r >> $ST; [ $r = 0 ] || exit 1
S12=$(sha256sum < $P/plan_ffr2_c3.json | cut -c1-12); cp $P/plan_ffr2_c3.json $P/plan_frame_spine_$S12.json; echo SHA=$S12 >> $ST
echo DONE >> $ST

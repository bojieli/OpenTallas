#!/usr/bin/env bash
# DIE-HBM-96: asbuilt_sources.json from a sibling elab (the bind_e0 tree has none), then bind + verify + hub dry on bind_F3d.
set -u
S=/srv/opentallas-scratch2/claude/die-hbm-93/src_mclk
P=/srv/opentallas-scratch2/claude/die-hbm-93/plan_final3/die_plan.json
D=/srv/opentallas-scratch2/claude/die-hbm-96/bind
A=$D/asbuilt_p37su5_sm_lat_vK3.json
LOG=$D/logs/bind_F3e.log
export PYTHONDONTWRITEBYTECODE=1
cd $S
rm -rf $D/elab_src; mkdir -p $D/elab_src
python3 tools/die_plan/bind.py elab $P --out $D/elab_src --asbuilt $A --mem 32 > $LOG 2>&1
rc=$?; echo RC_ELAB $rc >> $LOG; [ $rc = 0 ] || exit $rc
test -s $D/elab_src/asbuilt_sources.json || { echo RC_ELAB nofile >> $LOG; exit 1; }
cp $D/elab_src/asbuilt_sources.json $D/bind_F3d/asbuilt_sources.json
python3 tools/die_plan/bind.py bind $P --out $D/bind_F3d --asbuilt $A --mem 32 --strict >> $LOG 2>&1
rc=$?; echo RC_BIND $rc >> $LOG; [ $rc = 0 ] || exit $rc
python3 tools/die_plan/bind.py verify $P --out $D/bind_F3d --asbuilt $A --mem 32 --strict >> $LOG 2>&1
rc=$?; echo RC_VERIFY $rc >> $LOG; [ $rc = 0 ] || exit $rc
env TYPES="q_hub_nw q_hub_ne" bash $D/dry_hubs_F3d.sh >> $LOG 2>&1
echo RC_DRY $? >> $LOG

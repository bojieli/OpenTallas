#!/usr/bin/env bash
# DIE-HBM-96: strict bind + verify on the bind_e0 elaboration with vK3, then the hub dry.
set -u
S=/srv/opentallas-scratch2/claude/die-hbm-93/src_mclk
P=/srv/opentallas-scratch2/claude/die-hbm-93/plan_final3/die_plan.json
D=/srv/opentallas-scratch2/claude/die-hbm-96/bind
A=$D/asbuilt_p37su5_sm_lat_vK3.json
LOG=$D/logs/bind_F3d.log
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $D/logs
rm -rf $D/bind_F3d; mkdir -p $D/bind_F3d
ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $D/bind_F3d/asbuilt.json
cd $S
python3 tools/die_plan/bind.py bind $P --out $D/bind_F3d --asbuilt $A --mem 32 --strict > $LOG 2>&1
rc=$?
echo RC_BIND $rc >> $LOG
[ $rc = 0 ] || exit $rc
python3 tools/die_plan/bind.py verify $P --out $D/bind_F3d --asbuilt $A --mem 32 --strict >> $LOG 2>&1
rc=$?
echo RC_VERIFY $rc >> $LOG
[ $rc = 0 ] || exit $rc
env TYPES="q_hub_nw q_hub_ne" bash $D/dry_hubs_F3d.sh >> $LOG 2>&1
echo RC_DRY $? >> $LOG

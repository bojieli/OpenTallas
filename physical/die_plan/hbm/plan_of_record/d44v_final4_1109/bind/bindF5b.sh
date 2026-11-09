#!/usr/bin/env bash
# HBM-PLAN-1: strict bind of the composed final-switch plan (p6_relay), same recipe as DIE-HBM-96 bindF3d (bind_e0 elaboration, vK3 inputs) + vK5b (vK5 + R8 table regenerated for p6_relay).
set -u
S=/srv/opentallas-scratch2/claude/hbm-plan-1/src_f4
P=/srv/opentallas-scratch2/claude/hbm-plan-1/stage/p6_relay/die_plan.json
D=/srv/opentallas-scratch2/claude/hbm-plan-1/bind
A=$D/asbuilt_p37su5_sm_lat_vK5b.json
O=$D/bind_F5b
LOG=$D/logs/bind_F5b.log
export PYTHONDONTWRITEBYTECODE=1
rm -rf $O; mkdir -p $O
ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $O/asbuilt.json
cd $S
python3 tools/die_plan/bind.py bind $P --out $O --asbuilt $A --mem 32 --strict > $LOG 2>&1
echo RC_BIND $? >> $LOG

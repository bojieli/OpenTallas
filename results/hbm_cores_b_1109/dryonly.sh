#!/usr/bin/env bash
set -u
D=/srv/opentallas-scratch2/claude/die-hbm-96/bind
env TYPES="q_hub_nw q_hub_ne" bash $D/dry_hubs_F3d.sh > $D/logs/dry_F3d.log 2>&1
echo RC_DRY $? >> $D/logs/dry_F3d.log

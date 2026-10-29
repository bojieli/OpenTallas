#!/bin/bash
cd /srv/opentallas-scratch2/claude/die-qc5-1028
./runKit.sh K3 /srv/opentallas-scratch2/claude/die-qc5-1028/plan_grpPm/event/qc_grpPm_event.json /srv/opentallas-scratch2/claude/die-qc5-1028/regions_grpPm.json /srv/opentallas-scratch2/claude/die-qc5-1028/feed_grpPm.json --region-dme delay --region-dme-only c_W5_bf_01 && PLAN=/srv/opentallas-scratch2/claude/die-qc5-1028/plan_grpPm/event/qc_grpPm_event.json MAP=/srv/opentallas-scratch2/claude/die-qc5-1028/regions_grpPm.json ./chainK.sh K3

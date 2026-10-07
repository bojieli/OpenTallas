#!/bin/bash
cd /srv/opentallas-scratch/claude/takeover-ds/window-source/src
/srv/opentallas-scratch/admit.sh 32 -- python3 tools/dsrom_window_source_ctl_physical.py --out /srv/opentallas-scratch/claude/takeover-ds/window-source/route_r2 --execute > /srv/opentallas-scratch/claude/takeover-ds/window-source/route_r2.log 2>&1
echo $? > /srv/opentallas-scratch/claude/takeover-ds/window-source/route_r2.rc

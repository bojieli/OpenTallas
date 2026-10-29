#!/usr/bin/env bash
python3 /srv/opentallas-scratch2/claude/wt/hbm-bind-4-1029/results/hbm_bind_4_1029/mem_island_lockstep.py /srv/opentallas-scratch2/claude/hbm-bind-4-1029/dce/asbuilt.json /srv/opentallas-scratch2/claude/hbm-bind-4-1029/memlock > /srv/opentallas-scratch2/claude/hbm-bind-4-1029/memlock.log 2>&1; rc=$?; tail -3 /srv/opentallas-scratch2/claude/hbm-bind-4-1029/memlock.log; exit $rc

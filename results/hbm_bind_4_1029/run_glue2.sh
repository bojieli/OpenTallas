#!/usr/bin/env bash
python3 /srv/opentallas-scratch2/claude/wt/hbm-bind-4-1029/results/hbm_bind_4_1029/glue_equiv.py /srv/opentallas-scratch2/claude/hbm-bind-4-1029/glue/helpers /srv/opentallas-scratch2/claude/hbm-bind-4-1029/glue/equiv > /srv/opentallas-scratch2/claude/hbm-bind-4-1029/glue2.log 2>&1; rc=$?; cat /srv/opentallas-scratch2/claude/hbm-bind-4-1029/glue2.log | tail -13; exit $rc

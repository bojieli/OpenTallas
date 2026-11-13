#!/bin/bash
cd /srv/opentallas-scratch3/claude/frame-forms-1/all1
python3 -I /srv/opentallas-scratch3/claude/wt/frame-forms-1/events/s81_frame_spine_1113/compose_frame_spine.py /srv/opentallas-scratch3/claude/frame-forms-1/w/plan_A.json merged.json --shards $(ls -d /srv/opentallas-scratch3/claude/frame-forms-1/all1/sh/*/ | sed "s#/\$##" | paste -sd,) --report compose_report.json --tsv compose_report.tsv > compose.log 2>&1; echo COMPOSE_RC=$?
python3 -I /srv/opentallas-scratch3/claude/wt/frame-forms-1/events/s81_frame_spine_1113/finalize.py /srv/opentallas-scratch3/claude/frame-forms-1/w/plan_A.json merged.json plan_fin.json > finalize.log 2>&1; echo FIN_RC=$?; cat finalize.log

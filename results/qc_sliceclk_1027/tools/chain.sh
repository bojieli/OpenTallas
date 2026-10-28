#!/bin/bash
cd /srv/opentallas-scratch2/claude/qc-sliceclk-1027
~/.local/bin/ot-run --mem 32 --threads 4 --hosts localhost --dir /srv/opentallas-scratch2/claude/qc-sliceclk-1027/trial --priority die -- bash run_clock.sh > /srv/opentallas-scratch2/claude/qc-sliceclk-1027/clock_run.log 2>&1; echo "clock rc $? $(date)" >> /srv/opentallas-scratch2/claude/qc-sliceclk-1027/chain.log
~/.local/bin/ot-run --mem 256 --threads 16 --hosts localhost --dir /srv/opentallas-scratch2/claude/qc-sliceclk-1027/trial --priority die -- bash run_grt.sh > /srv/opentallas-scratch2/claude/qc-sliceclk-1027/grt_run.log 2>&1; echo "grt rc $? $(date)" >> /srv/opentallas-scratch2/claude/qc-sliceclk-1027/chain.log

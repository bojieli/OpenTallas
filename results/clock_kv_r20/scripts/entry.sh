#!/bin/bash
cd /srv/opentallas-scratch2/claude/clock-kv-r19-1027/slice; ulimit -v 48000000; export PYTHONPATH=/srv/opentallas-scratch2/claude/wt/clock-kv-r20/tools/die_plan
python3 /srv/opentallas-scratch2/claude/wt/clock-kv-r20/tools/die_plan/kv_r20_entry_capture.py pd/hm_r12.json --out /srv/opentallas-scratch2/claude/clock-kv-r20-1027/slice/mp_r20 --entries /srv/opentallas-scratch2/claude/kv-core-slice-1-1027/entries.json --mesh /srv/opentallas-scratch2/claude/clock-kv-r15-1026/r15 --no-render --dump /srv/opentallas-scratch2/claude/clock-kv-r20-1027/slice/entry_rows.json > /srv/opentallas-scratch2/claude/clock-kv-r20-1027/slice/mp_r20.log 2>&1
echo "rc=$? $(date -Is)" > /srv/opentallas-scratch2/claude/clock-kv-r20-1027/slice/entry.run

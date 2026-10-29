#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/die-head-24-bind
python3 tools/s81_head/head_die_portbind.py results/die_head_21_1028/hk3/plan_hk3_dh24.json --out results/die_head_24_bind/hk3
echo HEAD_PORTBIND_RC=$?

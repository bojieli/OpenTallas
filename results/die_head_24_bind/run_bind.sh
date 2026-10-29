#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/die-head-24-bind
python3 tools/s81_head/head_die_portbind.py results/die_head_21_1028/hk4/plan_rx_tx_dh24.json --out results/die_head_24_bind/hk4_rx_tx
echo HEAD_PORTBIND_RC=$?

#!/bin/bash
set -uo pipefail
cd /srv/opentallas-scratch/claude/hd4g/gen2e4/tailcls/src
python3 tools/hbm_die_v16/d4g_relay_splice.py ../pre_relay.json ../tail_cls_layer.json.gz ../tail_cls_contract.json --report ../tail_cls_splice.json > ../tail_cls_splice.log 2>&1
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh ../tail_cls_contract.json ../tail_cls_bind > ../tail_cls_bind.out 2>&1
echo STRICT_BIND_EXIT=$?
cat ../tail_cls_splice.log; tail -1 ../tail_cls_bind/port_bind.log

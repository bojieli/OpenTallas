#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/die-kv-6
export HOME=/home/ubuntu
for d in 0 15; do for r in 1 31 63 66 70 74 95; do tools/qwen_kv_die/kv_bootage_bench.sh /srv/opentallas-scratch2/claude/die-kv-11-1028/vport_rt95 vport 0 D=$d R=$r DB=15 RB=95 | tail -1; done; done
for m in 1 2 3 4 5 6 7 8; do tools/qwen_kv_die/kv_bootage_bench.sh /srv/opentallas-scratch2/claude/die-kv-11-1028/vport_rt95 vport $m D=15 R=74 DB=15 RB=95 | tail -1; done
echo DONE

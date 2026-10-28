#!/bin/bash
# DIE-KV-12: vport RT bound 95 lockstep bench with phase D (K/V-flag injection), controls + mutants 1-8
cd /srv/opentallas-scratch2/claude/wt/die-kv-6; export HOME=/home/ubuntu; O=/srv/opentallas-scratch2/claude/die-kv-12-1028/vport95
for d in 0 15; do for r in 1 31 63 66 70 74 95; do tools/qwen_kv_die/kv_bootage_bench.sh $O vport 0 D=$d R=$r DB=15 RB=95 | tail -n 1; done; done
for r in 74 95; do for m in 1 2 3 4 5 6 7 8; do tools/qwen_kv_die/kv_bootage_bench.sh $O vport $m D=15 R=$r DB=15 RB=95 | tail -n 1; done; done
tools/qwen_kv_die/kv_bootage_bench.sh $O vport 0 D=3 R=17 DB=15 RB=63 | tail -n 1
tools/qwen_kv_die/kv_bootage_bench.sh $O vport 3 D=3 R=17 DB=15 RB=63 | tail -n 1
echo DONE

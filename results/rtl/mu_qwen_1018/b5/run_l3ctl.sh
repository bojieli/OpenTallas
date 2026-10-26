#!/bin/bash
# MU-QW-DIE B5 (10-19): per-user goldens for MU users 1..3 = the same released prompt at positions 8190 / 8189 / 8188
# (user 0 = P8191), layers L0..L2 history-seeded from fx/history_l3 (L0..L2 real prefill K/V, pin L0_die0 match).
# Decoding P reads only K/V slots < P (+ its own write), so the seeded output at P equals the true prefill golden.
set -u
B=/srv/opentallas-scratch/claude/tokpass-qwen-1018; O=/srv/opentallas-scratch/claude/mu-qw-die/b5/l3ctl
mkdir -p $O; cd $B/src
export PYTHONPATH=/srv/opentallas-scratch/claude/tokpass-qwen-1018/pylib QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 OMP_NUM_THREADS=16
/usr/bin/python3.14 tools/qwen_hbmacc_position_oracle_gpu.py --run --device cpu --prep-dir $B/fx/prep/tp4 --layers 3   --tokens $B/fx/inputs/prompt_tokens_8192.txt --positions 8191 --embedding-npz $B/fx/inputs/prompt_embedding.npz   --kv-history $B/fx/history_l3 --out $O > $O.log 2>&1
echo "l3seed rc=$?" >> $O.log

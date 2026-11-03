#!/bin/bash
# DIE-KV-61/grt (= DIE-KV-58 nom58.sh: 12.25 die STA, die_sta_related, nominal margin, cppr-lca, count-align bind, HB4, inv clock, core insertion view)
# + qkd_ectlk_q1 view (8 signed core views) + OWNER 11-02 hold >= 0 (pair_slack_gate.HOLD_MIN_PS = 0 via hold0 wrapper; tool default 10)
#   nom61.sh PROOF PLAN OUT BIND
set -u
P=$1; PL=$2; T=$3; B=/home/ubuntu/scratch-root/claude/die-kv-61/grt; S=$B/wt/tools/die_plan; X=$B/in/codex-kv-1030
CV=(); for n in 1 2 5 6; do M=kv3_head_eighth_e$n; CV+=(--core-view "$M=$B/in/autopilot/closed/qwen_kvsys/${M}__3e7fccd216/view/$M"); done
for M in kv3_head_eighth_e0 qkd_ectlk_q0 qkd_ectlk_q3; do CV+=(--core-view "$M=$X/dsr_views/$M"); done
CV+=(--core-view "qkd_ectlk_q1=$B/views/qkd_ectlk_q1")
rm -rf $T; mkdir -p $T; cp -a $X/regchar $T/
python3 $B/hold0.py $S $P --plan $PL --out $T --margin-policy nominal --cppr-lca --count-align $4 --count-align-key region --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv "${CV[@]}" --core-insertion view --count-align-ss-scale 0 > $T.log 2>&1
echo "STA rc=$? $(date)" >> $T.log
python3 $B/gate.py $T >> $T.log 2>&1

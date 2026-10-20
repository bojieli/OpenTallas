#!/bin/bash
# REFILL-1725/QWLAYER: stage three source cohorts (today's changed Qwen MU sources; they do not merge cleanly) on ot-epyc6.
set -u; h=ot-epyc6; D=/srv/opentallas-scratch/claude/refill-1725/QWLAYER
P="rtl tools physical/asap7_memory_macros physical/asap7_memory_macros_v2 results/rtl/mu_qwen_1018 results/rtl/qwen_layer_tput_1018 results/rtl/q_collcal_1018 results/rtl/qcollcal_rl_1018 results/arch/qwen_split_compute_1014/landfix_q_1018 results/arch/qwen_kv_static_programme_1017"
ssh -o ControlPath=none -o ConnectTimeout=15 $h "set -e; G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git; git -C \$G fetch -q origin claude/qw-ctlm4-1019 claude/qw-sysface3-1019 codex/qwen-gen3-takeover3-1019 claude/qw-sram3-1019
for c in ctlm4:d60ab0461 sysface3:83fc1f355 gen3c:864d10c8e; do n=\${c%%:*}; s=\$(git -C \$G rev-parse \${c#*:}); rm -rf $D/\$n/src; mkdir -p $D/\$n/src $D/\$n/out; git -C \$G archive \$s $P | tar -x -C $D/\$n/src; echo \$s > $D/\$n/src/SOURCE_COMMIT; find $D/\$n/src/results/rtl/mu_qwen_1018 -type d -name runs -prune -exec rm -rf {} +; du -sh $D/\$n/src; done"
rsync -a -e 'ssh -o ControlPath=none' /home/ubuntu/scratch/mu-qwen-adopt/head/ $h:$D/head/
echo staged $h

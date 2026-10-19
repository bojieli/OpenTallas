#!/bin/bash
# REFILL-1225/QWREG stage merge candidate on ot-epyc7
set -u; h=ot-epyc7; S=715e572ace085894f342b4dfda2d302cb93f1165
D=/srv/opentallas-scratch/claude/refill-1225/QWREG
P="rtl tools physical/asap7_memory_macros physical/asap7_memory_macros_v2 results/rtl/mu_qwen_1018 results/rtl/mu_qwen_current_1019 results/rtl/qwen_layer_tput_1018 results/rtl/q_collcal_1018 results/rtl/qcollcal_rl_1018 results/arch/qwen_split_compute_1014/landfix_q_1018 results/arch/qwen_kv_static_programme_1017 results/rtl/qwen_coll_safe_1019"
ssh -o ControlPath=none -o ConnectTimeout=15 $h "set -e; G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git; git -C \$G fetch -q origin claude/qwreg-cur-1225; git -C \$G cat-file -t $S; rm -rf $D/src; mkdir -p $D/src $D/out; git -C \$G archive $S $P | tar -x -C $D/src; echo $S > $D/src/SOURCE_COMMIT; find $D/src/results/rtl/mu_qwen_1018 -type d -name runs -prune -exec rm -rf {} +; du -sh $D/src"
rsync -a -e 'ssh -o ControlPath=none' /home/ubuntu/scratch/mu-qwen-adopt/head/ $h:$D/head/
echo staged $h

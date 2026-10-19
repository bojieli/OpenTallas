#!/bin/bash
set -u; h=ot-epyc5; S=99e646e980879270342422338b6e3ad3c161c9da
D=/srv/opentallas-scratch/claude/refill-1330/MUKVREG
P="rtl tools physical/asap7_memory_macros physical/asap7_memory_macros_v2 results/rtl/mu_qwen_1018 results/rtl/kv_bootage_1019 results/rtl/qwen_layer_tput_1018 results/rtl/q_collcal_1018 results/rtl/qcollcal_rl_1018 results/arch/qwen_split_compute_1014/landfix_q_1018 results/arch/qwen_kv_static_programme_1017"
ssh -o ControlPath=none -o ConnectTimeout=15 $h "set -e; G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git; git -C \$G fetch -q origin claude/mu-die-kv-1019; git -C \$G cat-file -t $S; rm -rf $D/src; mkdir -p $D/src $D/out; git -C \$G archive $S $P | tar -x -C $D/src; echo $S > $D/src/SOURCE_COMMIT; rm -rf $D/src/results/rtl/mu_qwen_1018/{kv,hroot,host}/runs; du -sh $D/src; ls ~/.local/opentallas-tools/verilator-5.050/bin/verilator"
rsync -a -e 'ssh -o ControlPath=none' /home/ubuntu/scratch/mu-qwen-adopt/head/ $h:$D/head/
echo staged

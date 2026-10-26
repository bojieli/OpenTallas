#!/bin/bash
# QW-GEN3 10-19: stage + launch phase 1 of dv2f19g3 (overlay = git diff 0d4c9808f..H on dv2f18dh2 src).  usage: stage.sh H
set -u
H=${1:?commit}; T=${2:-dv2f19g3}; R=/srv/opentallas-scratch/claude/mu-die-qw; Q=/srv/opentallas-scratch/claude/qwen-split-compute; D=/home/ubuntu/scratch/qw-gen3; SRC=$R/dv2f18dh2
git -C /home/ubuntu/OpenTallas diff --name-only --diff-filter=AMR 0d4c9808f $H > $D/ov.txt
ssh -o ControlPath=none ot-epyc6 "set -e; [ ! -e $R/$T ] || { echo exists; exit 1; }; mkdir -p $R/$T; cp -a --reflink=auto $SRC/src $R/$T/src; cp $SRC/land_plan_bi_chain.json $R/$T/; ln -sfn $R/$T $Q/$T" || exit 3
git -C /home/ubuntu/OpenTallas archive $H $(cat $D/ov.txt) | ssh -o ControlPath=none ot-epyc6 "cd $R/$T/src && tar xf -" || exit 5
ssh -o ControlPath=none ot-epyc6 "echo '$H (claude/qw-gen3-1019 QW-GEN3 successor of dv2f19g2; overlay on dv2f18dh2 src 0d4c9808f)' > $R/$T/src/SOURCE_COMMIT"
for f in gen.sh run.sh chain.sh pre.sh relay_side.sh; do ssh -o ControlPath=none ot-epyc6 "cat > $R/$T/$f" < $D/$T/$f; done
printf 'PILOT_NOT_A_GATE: QW-GEN3 die run with DECLARED stand-ins (src/results/rtl/qw_gen3_1019/README.md)\n' | ssh -o ControlPath=none ot-epyc6 "cat > $R/$T/PILOT_NOT_A_GATE; chmod +x $R/$T/*.sh"
ssh -o ControlPath=none ot-epyc6 "cd $R/$T/src && grep -c OT_SPLIT_LAND_LIST tools/qwen_rom_fulldie_b3r2.py && grep -c qfd_mu_ctx_rx_die tools/qwen_split/dv_case.py && ls results/arch/qw_dieclk2_1019/landing_list.json" || exit 6
echo "$(date '+%F %T') staged $T @ $H"
exec /home/ubuntu/bin/ot-run --priority die --mem 48 --dir $R -- bash $R/$T/pre.sh

#!/bin/bash
# TOKe-QWM 10-23: stage the Qwen 9-stage token run on ONE current-main assembly across gold1/gold2/ep7/ep9
set -eu
ASM=92c2417f6; RR=/srv/opentallas-scratch/claude/tokqwm-1023; L=/home/ubuntu/scratch/tokqwm-1023
G1=/srv/opentallas-scratch/claude
T=$L/src_$ASM.tar
[ -s $T ] || git -C /home/ubuntu/OpenTallas archive -o $T $ASM rtl tools configs physical/asap7_memory_macros
for h in ot-gold1 ot-gold2 ot-epyc7 ot-epyc9; do
  ssh $h "mkdir -p $RR/src_$ASM $RR/tokfunc_tools && test -f $RR/src_$ASM/ASM_COMMIT" || {
    ssh $h "tar -x -C $RR/src_$ASM" < $T && ssh $h "echo $ASM > $RR/src_$ASM/ASM_COMMIT"; }
  ssh $h "ln -sfn src_$ASM $RR/src && cp -a $RR/src/tools/qwen_tokfunc/. $RR/tokfunc_tools/"
done
# gold1: stg (shared fx_in + finished golden fixtures, reused via --fx) + head fixtures
ssh ot-gold1 "mkdir -p $RR/stg $RR/head && ln -sfn $G1/tokfunc-qw-1021/stg/fx_in $RR/stg/fx_in && cp -a $G1/tokd-qw-main-1023/head/fx $RR/head/ && cp -a $G1/tokqw4-1022/stg3/fx $RR/stg_fx_reuse"
# gold2: xt1 inputs
ssh ot-gold2 "mkdir -p $RR/xt1"; ssh ot-gold1 "tar -C $G1/tokd-qw-main-1023/xt1 -ch in" | ssh ot-gold2 "tar -x -C $RR/xt1"
# ep7: link stages + xdie fixtures
for s in tp8 ovl4u ctx4u xdie; do ssh ot-epyc7 "mkdir -p $RR/$s"; ssh ot-gold1 "tar -C $G1/tokd-qw-main-1023/$s -ch fx" | ssh ot-epyc7 "tar -x -C $RR/$s"; done
ssh ot-gold1 "cd $G1/tokd-qw-main-1023 && sha256sum link_fixtures.sha256 >/dev/null && cat link_fixtures.sha256" > $L/link_fixtures.prior.sha256
ssh ot-epyc7 "cd $RR && find tp8/fx ovl4u/fx ctx4u/fx -type f | sort | xargs sha256sum" > $L/link_fixtures.sha256
# ep9: kv fixtures + r17 explicit child-archive packet (from ep5) + chain inputs (stg fixtures + P8191 windows from gold1)
ssh ot-epyc9 "mkdir -p $RR/kv $RR/kv_pkt $RR/chain/in/fx $RR/chain/in/p8191"
ssh ot-epyc5 "tar -C /srv/opentallas-scratch2/claude/tokqw4-1022/kv -ch fx" | ssh ot-epyc9 "tar -x -C $RR/kv"
ssh ot-epyc5 "tar -C /srv/opentallas-scratch2/claude/codex-tok-qw-2000/r17_explicit_packet -ch obj" | ssh ot-epyc9 "tar -x -C $RR/kv_pkt"
ssh ot-gold1 "cd $G1/tokqw4-1022/stg3/fx && tar -ch L*_fixture.json L*.npz" | ssh ot-epyc9 "tar -x -C $RR/chain/in/fx"
ssh ot-gold1 "cd $G1/tokfunc-qw-1021/stg/fx_in/P8191 && tar -ch x_preload.hex embedding_row.json L*_die0_x.hex kv_pre/L*_die0.npy" | ssh ot-epyc9 "tar -x -C $RR/chain/in/p8191"
ssh ot-epyc9 "touch $RR/chain/in/.complete"
echo STAGED

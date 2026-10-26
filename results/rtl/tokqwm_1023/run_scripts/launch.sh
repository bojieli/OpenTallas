#!/bin/bash
# TOKe-QWM 10-23: launch the 9 Qwen token stages on assembly 92c2417f6 (RUNROOT tokqwm-1023 on gold1/gold2/ep7/ep9)
RR=/srv/opentallas-scratch/claude/tokqwm-1023; L=/home/ubuntu/scratch/tokqwm-1023; TT=$RR/tokfunc_tools
R=/home/ubuntu/bin/ot-run
run(){ local s=$1 mem=$2; shift 2; nohup $R --mem $mem --threads 48 --dir $RR/$s -- "$@" > $L/logs/$s.otrun.log 2>&1 < /dev/null & echo "$s pid $!"; }
run stg   240 bash $TT/stage_stg.sh $RR --su-lt 0 --fx $RR/stg_fx_reuse
run head  16  bash $TT/stage_head.sh $RR
run xt1   320 bash $TT/stage_xt1.sh $RR
run tp8   64  bash $TT/stage_tp8.sh $RR
run ovl4u 64  bash $TT/stage_ovl4u.sh $RR --release-masters
run ctx4u 32  bash $TT/stage_ctx4u.sh $RR
run xdie  64  bash $TT/stage_xdie.sh $RR
# kv: explicit r17 genuine-archive binding (measured peak 9.3 GB on QW4, n=3) -> chain on its binary (measured 47.6 GB)
( $R --mem 64 --threads 16 --dir $RR/kv -- bash $TT/stage_kv.sh $RR --explicit-r17 $RR/kv_pkt/obj > $L/logs/kv.otrun.log 2>&1 < /dev/null
  $R --mem 160 --threads 46 --dir $RR/chain -- bash $TT/stage_chain.sh $RR --kv-obj $RR/kv/out --par 46 > $L/logs/chain.otrun.log 2>&1 < /dev/null ) &
echo "kv+chain pid $!"

#!/bin/bash
# TOKe-QWM: after stg -> attnret on the stg objects (gold1) -> collect all 9 + compose (xhead/attnret optional slots)
RR=/srv/opentallas-scratch/claude/tokqwm-1023; L=/home/ubuntu/scratch/tokqwm-1023; TT=$RR/tokfunc_tools
until grep -q 'ot-run: RAN\|ot-run: .*exit' $L/logs/stg.otrun.log; do sleep 30; done
ssh ot-gold1 "mkdir -p $RR/attnret $RR/stg_objs && for c in rel pos; do ln -sfn $RR/stg/\$c/build/obj_n12 $RR/stg_objs/\$c; done"
/home/ubuntu/bin/ot-run --mem 32 --threads 8 --dir $RR/attnret -- bash $TT/stage_attnret.sh $RR stg $RR/stg_objs > $L/logs/attnret.otrun.log 2>&1 < /dev/null
TOKFUNC_HOSTS="ot-gold1 ot-gold2 ot-epyc7 ot-epyc9" TOKFUNC_KVHOSTS=ot-epyc9 bash $L/tools/run_tok_func_qw.sh --asm 92c2417f6 --collect-only \
  --runroot $RR --kvroot $RR --stage-dir ovl4u=ovl4u_rel --out $L/run > $L/logs/collect.log 2>&1 < /dev/null
mkdir -p $L/run/results/attnret $L/run/results/xhead
ssh ot-gold1 "cat $RR/attnret/result.json" > $L/run/results/attnret/result.json
cp $L/xhead/result.json $L/run/results/xhead/
python3 -I $L/tools/compose_tokfunc.py --results $L/run/results --out $L/run/compose --asm 92c2417f6 --grade 'RTL-functional (source assembly)' --repo /home/ubuntu/OpenTallas > $L/logs/compose.log 2>&1
echo "FINISH rc $?" >> $L/logs/compose.log

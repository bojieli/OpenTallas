#!/bin/bash
# ti_dry.sh : tap_ident new vs old (.bak1113) on the ev2st tap_ident input + new on ev2st plan_final (idempotency)
set -u; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event2}
POR=physical/die_plan/qwen_compute/plan_of_record; W=$B/work/ti_dry; mkdir -p $W; cd $E
cp $B/in/zz_c6b_fix.json $POR/zz_tid_ref.json
for v in new old; do
  S=$B/tap_ident.py; [ $v = old ] && S=$B/tap_ident.py.bak1113
  cp $B/work/ev2st/p3_repick.json $POR/zz_tid_in.json
  python3 -I $S $POR/zz_tid_ref.json $POR/zz_tid_in.json --out $W/out_$v.json --report $W/rep_$v.json --eq $W/eq_$v.tsv > $W/$v.log 2>&1; echo "$v rc=$?" >> $W/$v.log
done
cp $B/work/ev2st/plan_final.json $POR/zz_tid_in.json
python3 -I $B/tap_ident.py $POR/zz_tid_ref.json $POR/zz_tid_in.json --out $W/out_idem.json --report $W/rep_idem.json --eq $W/eq_idem.tsv > $W/idem.log 2>&1; echo "idem rc=$?" >> $W/idem.log
rm -f $POR/zz_tid_ref.json $POR/zz_tid_in.json
for v in new old idem; do tail -2 $W/$v.log | cut -c1-260; done
cmp -s $W/out_new.json $W/out_old.json && echo "DIFF new vs old: 0 (identical plans)" || { echo "DIFF new vs old:"; diff <(python3 -I -c "import json,sys;F=json.load(open(sys.argv[1]));[print(tn,q['name'],q.get('source_clock_port')) for tn,t in sorted(F['partition_types'].items()) for q in ((t.get('clock') or {}).get('landing_contract') or {}).get('pins',[]) if q.get('kind')=='clock' and q.get('dir')=='out']" $W/out_old.json) <(python3 -I -c "import json,sys;F=json.load(open(sys.argv[1]));[print(tn,q['name'],q.get('source_clock_port')) for tn,t in sorted(F['partition_types'].items()) for q in ((t.get('clock') or {}).get('landing_contract') or {}).get('pins',[]) if q.get('kind')=='clock' and q.get('dir')=='out']" $W/out_new.json); }
cmp -s $W/out_new.json $B/work/ev2st/p3b_taps.json && echo "new == chain p3b_taps" || echo "new != chain p3b_taps"

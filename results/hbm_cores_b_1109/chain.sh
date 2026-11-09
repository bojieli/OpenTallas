#!/bin/bash
# KV-TYPES-6: compose PV spreads + START re-derive + PV forward +1 -> strict bind1 -> raw branches -> strict bind2 (private)
cd /
set -uo pipefail
P=/srv/opentallas-scratch2/claude/kv-types-6/pv
PL=$P/plan
W=/srv/opentallas-scratch2/claude/kv-types-6/wt
KV=/srv/opentallas-scratch2/claude/kv-types-5/ev
CX=/srv/opentallas-scratch2/claude/codex-kv-types-1113
L=$P/chain.log
log(){ echo "$(date '+%F %T') $*" >> $L; }
die(){ log "STOP: $*"; exit 1; }
HV="/usr/local/bin/ot-heavy --mem 16"
until grep -q ALLDONE $P/par/done.txt 2>/dev/null; do sleep 30; done
log "spreads: $(tr '\n' ';' < $P/par/done.txt)"
SP="kv3_pv_v2 kv3_pv_v2n kv3_pv_v4 kv3_pv_v4n kv3_pv_v5 kv3_pv_v5n kv3_pv_v6 kv3_pv_v6n"
for t in kv3_pv_v7 kv3_pv_v12; do grep -q "^$t rc 0" $P/par/done.txt && SP="$SP $t" || log "NOT spread (keep plan_c.is band): $t"; done
mkdir -p $PL
for f in $KV/plan_kvr8/*; do b=$(basename $f); [ "$b" = plan_c.json ] || ln -sfn $f $PL/$b; done
ln -sfn plan_c.json $PL/die_plan.json
python3 -I -B $P/compose_spreads.py $CX/../type-safe-2-1108/kv/ev/plan_c.ch.json $P/par $CX/typesafe/plan_safe_before_pv_spread.json $PL/plan_s0.json $P/rep_s0.json $SP >> $L 2>&1 || die compose
# overlay src: wave src + my reset_tree
R=$(readlink -f /srv/opentallas-scratch2/claude/kw35/src_e2rd)
O=/srv/opentallas-scratch3/claude/kv-types-6/src_rs
if [ ! -d $O ]; then mkdir -p $(dirname $O); cp -al "$R" $O || die overlay; find $O -type d -exec chmod u+w {} + ; rm -f $O/tools/die_plan/reset_tree.py; cp $W/tools/die_plan/reset_tree.py $O/tools/die_plan/reset_tree.py; fi
cd $W
START_TYPES="$SP kv3_pv kv3_pv_v8 kv3_hub_Wi"
tl=$(echo $START_TYPES | tr ' ' ',')
if ! $HV --tag kv6-start -- python3 -I -B tools/die_plan/kv_start_corridor_event.py start $PL/plan_s0.json $PL/plan_s1.json $P/rep_s1.json --types $tl >> $L 2>&1; then
  log "start with hub_Wi failed, retry without"; tl=$(echo $SP kv3_pv kv3_pv_v8 | tr ' ' ',')
  $HV --tag kv6-start -- python3 -I -B tools/die_plan/kv_start_corridor_event.py start $PL/plan_s0.json $PL/plan_s1.json $P/rep_s1.json --types $tl >> $L 2>&1 || die start
fi
log "start ok types $tl"
python3 -I -B $CX-src/results/geom_review/kv_types_safe_1113/pv_forward_station.py $PL/plan_s1.json $PL/plan_s2.json $P/rep_s2.json >> $L 2>&1 || die pv_forward
bindrun(){ # plan outdir
  mkdir -p $2; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $KV/bind_kvr8/$f ] && cp -l $KV/bind_kvr8/$f $2/ 2>/dev/null; done
  ( cd $O && $HV --tag kv6-bind -- python3 -I -B $O/tools/die_plan/bind.py bind $1 --out $2 --asbuilt $PL/asbuilt.json --strict ) > $2.log 2>&1
  python3 -I -c "import json,sys;r=json.load(open(sys.argv[1]));print('BIND',sys.argv[1],'errors',r.get('n_errors'),[str(e)[:200] for e in (r.get('errors') or [])[:6]] if isinstance(r.get('errors'),list) else r.get('errors'))" $2/bind_report.json >> $L 2>&1 || log "no report $2"
}
bindrun $PL/plan_s2.json $P/bind1
python3 -I -c "import json,sys;sys.exit(0 if json.load(open('$P/bind1/bind_report.json')).get('n_errors')==0 else 1)" || die bind1
cd $W
RT=$(echo $SP kv3_pv kv3_pv_v8 kv3_pv_v1 kv3_pv_v1n kv3_pv_v3 kv3_pv_v3n | tr ' ' ',')
$HV --tag kv6-raw -- python3 -I -B tools/die_plan/kv_start_corridor_event.py raw $PL/plan_s2.json $PL/plan_c.json $P/rep_raw.json --types $RT --bind-rtl $P/bind1/rtl >> $L 2>&1 || die raw
bindrun $PL/plan_c.json $P/bind2
python3 -I -c "import json,sys;sys.exit(0 if json.load(open('$P/bind2/bind_report.json')).get('n_errors')==0 else 1)" || die bind2
md5sum $PL/plan_c.json >> $L
log CHAIN_DONE

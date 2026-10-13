#!/bin/bash
# qwen-tp8/die it1: TP8 track-A ROM die (recipe tp8a) = e8 chain recipe: localhost prep (gen needs scipy; niced, single
# thread) -> contract re-derive + tree-pad check -> element libs (assumed + r21b ETMs, copied from the qwendie e8 prep since
# EPYC3 drains) -> die_views (closed views per bind_it1.json, contract-budget 0.2T for the rest) -> die clock plan
# (htop + hreg --shards 12 on EPYC1, record, balance) -> EPYC1 die_chain (PDN, GRT, STA) + pad_chain (hold pads).
# usage: it1.sh   (env WT, L override)
set -u
WT=${WT:-/home/ubuntu/wt/el1011-qwen-tp8-die}; L=${L:-/tmp/claude-1000/tp8/it1}; K=$L/clk; H=ot-epyc1tb
B=/srv/opentallas-scratch/claude/qwen-tp8-die; R=$B/it1; T=$B/kit_it1/tools/qwen_kv_die/chain
E8=/tmp/claude-1000/qd1011/e8; S="ssh -o ControlPath=none $H"
RC=tp8a; C=$WT/results/arch/hier_contract_1012/qwen_rom_tp8.json
mkdir -p $L/lint $K; log() { echo "$(date '+%F %T %Z') $*" | tee -a $L/it1.log; }
cd $WT; log "it1 start src $(git rev-parse --short=9 HEAD)"
[ -f $L/case/run.tcl ] || nice python3 tools/qwen_rom_fulldie_b3r2.py pdn --recipe $RC --pdn-rev r5 --work $L/case > $L/gen.log 2>&1 || { log "GEN FAIL"; exit 1; }
git rev-parse --short=9 HEAD > $L/case/SOURCE_COMMIT; echo "--recipe $RC --pdn-rev r5" > $L/case/SOURCE_NOTE
log "case: $(tail -1 $L/gen.log | cut -c1-200)"
nice python3 tools/qwen_die_seam/tree_pads.py --die-v $L/case/die.v --out $L/tree_pads_check.json > $L/pads.log 2>&1; log "tree legs as placed: $(cat $L/pads.log)"
nice python3 tools/hier_contract/derive_tp8.py --v5 results/arch/hier_contract_1011/qwen_rom.json --case $L/case --out $L/qwen_rom_tp8.json \
  --source "tp8a it1 case (pdn r5, src $(git rev-parse --short=9 HEAD))" > $L/derive.log 2>&1
python3 - "$C" "$L/qwen_rom_tp8.json" >> $L/it1.log <<'P'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
k = lambda c: [(s['name'], s['cell'], s['origin'], s['outline'], s.get('pins')) for s in c['slots'][1:]]
print('contract vs it1 case:', 'slots SAME' if k(a) == k(b) else 'slots DIFFER', '| relays',
      a['die_top_logic']['total'], b['die_top_logic']['total'], '| slot share', b['floorplan']['slot_share'])
P
nice python3 tools/qwen_kv_die/die_audit.py $L/case --die-w $(sed -n 's/.*-die_area {0 0 \([0-9.]*\) .*/\1/p' $L/case/run.tcl | head -1) --out $L/audit.json > $L/audit.out 2>&1; log "die_audit: $(tail -1 $L/audit.out | cut -c1-300)"
nice python3 tools/die_top_lint.py lint --die qwen_rom --qwen-recipe $RC --out $L/lint > $L/lint.log 2>&1; log "lint $RC rc=$? $(tail -1 $L/lint.log | cut -c1-300)"
ST=$(ls $L/lint/*_stubs.sv 2>/dev/null | head -1); [ -n "$ST" ] || { log "NO STUBS"; exit 1; }
( nice python3 tools/qwen_die_element_lib.py --stubs $ST --lef $L/case/elements.lef --out $L/assumed &&
  nice python3 tools/qwen_die_etm_map.py --etm $E8/etm_in --lef $L/case/elements.lef --assumed $L/assumed --out $L/libs0 --recipe $RC \
    --stubs $ST --station-etm $E8/st --corners ss,tt,ff ) > $L/libs.log 2>&1 || log "ETM LIBS FAIL (assumed only)"
[ -f $L/libs0/views.json ] || { mkdir -p $L/libs0; cp $L/assumed/qfd_elements_*.lib $L/libs0/; }
nice python3 tools/hier_contract/die_views.py --libs $L/libs0 --lef $L/case/elements.lef --contract $C \
  --bind results/physical/die_iter_1012/qwen_rom_tp8/bind_it1.json --out $L/libs > $L/views.log 2>&1 || { log "VIEWS FAIL $(tail -2 $L/views.log)"; exit 1; }
log "views: $(tail -1 $L/views.log | cut -c1-300)"
$S "mkdir -p $R/case_r22k $R/libs" && rsync -a -e 'ssh -o ControlPath=none' $L/case/ $H:$R/case_r22k/ && \
  rsync -a -e 'ssh -o ControlPath=none' $L/libs/ $L/assumed $H:$R/libs/ || { log "RSYNC FAIL"; exit 1; }
nice python3 tools/budgets/extract_die.py --src . --die qwen_rom --qwen-recipe $RC --out $K/die.json.gz > $K/extract.log 2>&1 || { log "EXTRACT FAIL"; exit 1; }
for g in htop hreg; do nice python3 tools/budgets/clock_plan.py emit --die-model $K/die.json.gz --name tp8it1_$g --out $K/$g --group $g --max-region-um 2600 --max-merge-um 2600 $([ $g = hreg ] && echo --shards 12) >> $K/emit.log 2>&1 || { log "EMIT $g FAIL"; exit 1; }; done
(cd $K && tar czf ck.tgz htop hreg) && scp -q -o ControlPath=none $K/ck.tgz $H:/tmp/qtp8_it1ck.tgz
$S "mkdir -p $R/clock && tar xzf /tmp/qtp8_it1ck.tgz -C $R/clock && bash $R/clock/htop/run.sh && SHARD_PAR=6 bash $R/clock/hreg/run.sh; cd $R/clock && tar czf - htop/tree_*.txt htop/*.json hreg/*/tree_*.txt hreg/*/*.json hreg/*/retry" > $K/back.tgz
(cd $K && tar xzf back.tgz) && nice python3 tools/budgets/clock_plan.py record --die-model $K/die.json.gz --case $K/htop $(for d in $K/hreg/sh[0-9]*; do echo --case $d; done) --max-region-um 2600 --max-merge-um 2600 --out $K/plan.json > $K/record.log 2>&1 || { log "CTS RECORD FAIL"; exit 1; }
log "clock plan: $(tail -n 1 $K/record.log)"
nice python3 tools/budgets/clock_plan.py balance --plan $K/plan.json --die-model $K/die.json.gz --libs $L/libs --out $K/plan_bal.json > $K/balance.log 2>&1 || { log "BALANCE FAIL $(tail -2 $K/balance.log)"; cp $K/plan.json $K/plan_bal.json; }
log "balance: $(tail -n 1 $K/balance.log | cut -c1-300)"
scp -q -o ControlPath=none $K/plan.json $H:$R/clock/plan_rec.json && scp -q -o ControlPath=none $K/plan_bal.json $H:$R/clock/plan.json
(cd $WT && tar czf $L/tools.tgz tools/hbm_die_relay_sta.py tools/qwen_kv_die/chain) && scp -q -o ControlPath=none $L/tools.tgz $H:/tmp/qtp8_it1_tools.tgz
$S "mkdir -p $B/kit_it1 && tar xzf /tmp/qtp8_it1_tools.tgz -C $B/kit_it1 && echo \"\$(date '+%F %T %Z') qwen-tp8/die chain it1 start (src $(git -C $WT rev-parse --short=9 HEAD), clock plan)\" >> $R/STATUS.log && (setsid nohup bash -c 'bash $T/die_chain.sh r22k $R $B/kit_it1 && bash $T/pad_chain.sh r22k $R' > $B/it1_chain.out 2>&1 < /dev/null &)"
log "CHAIN LAUNCHED rc=$? -> $H:$R (STATUS.log)"

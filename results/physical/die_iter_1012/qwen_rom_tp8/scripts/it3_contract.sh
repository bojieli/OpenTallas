#!/bin/bash
# qwen-tp8/die it3 (contract v3 slot revision 2026-10-13): generator case with the live KV hub outline + the reserved VM
# envelope (tp8b f2 'ahub' / 'reserve': generator-native) -> relay ck -> freeze -> tree delay tiles re-placed on the new
# case (frozen_tree_delay_pads.py, VM envelope as keep-out) -> post-pass case (contract_v3_slots.py: die.v / place.tcl /
# elements.lef + overlap / reach / share checks) -> contract derive -> schema, tree alignment, relay ck, die_audit, lint.
# The case is left for the GRT / STA step (it2.sh from the element-lib step on).  usage: it3_contract.sh  (env WT, L)
set -u
WT=${WT:-/home/ubuntu/wt/claude-qwen-tp8-die-1013}; L=${L:-/home/ubuntu/scratch-qwen-tp8-die/it3}
RC=tp8b; C=$WT/results/arch/hier_contract_1012/qwen_rom_tp8.json; BASE=${BASE:-/home/ubuntu/scratch-qwen-tp8-die/it2/physical_model_actual_codex.json}
mkdir -p $L/lint; log() { echo "$(date '+%F %T %Z') $*" | tee -a $L/it3.log; }
cd $WT || exit 1; SRC=$(git rev-parse --short=9 HEAD); log "it3 start src $SRC"
[ -f $L/gen_case/run.tcl ] || nice python3 tools/qwen_rom_fulldie_b3r2.py pdn --recipe $RC --pdn-rev r5 --work $L/gen_case > $L/gen.log 2>&1 || { log "GEN FAIL $(tail -1 $L/gen.log | cut -c1-300)"; exit 1; }
echo $SRC > $L/gen_case/SOURCE_COMMIT; echo "--recipe $RC --pdn-rev r5" > $L/gen_case/SOURCE_NOTE
log "gen: $(tail -1 $L/gen.log | cut -c1-300)"
python3 tools/qwen_tp8/relay_ck_check.py $L/gen_case/die.v > $L/relay_ck_gen.log 2>&1; log "relay ck (gen) rc=$? $(cut -c1-200 $L/relay_ck_gen.log)"
[ -f ${TEMPLATE:-$L/plan/physical_model.json} ] || { log "NO plan/physical_model.json (run tools/qwen_tp8/cut_dump.py $L/plan first)"; exit 1; }
python3 tools/qwen_tp8/freeze_actual_case.py $L/gen_case ${TEMPLATE:-$L/plan/physical_model.json} $L/model_gen.json > $L/freeze.log 2>&1 || { log "FREEZE FAIL $(tail -1 $L/freeze.log | cut -c1-300)"; exit 1; }
KO=$(python3 -c "
import sys; sys.path.insert(0,'tools'); import die_top_lint as D
print(' '.join('--keepout '+','.join(str(q) for q in r['rect']) for r in D.QWEN_RECIPES['$RC']['tp8']['f2'].get('reserve',[])))")
nice python3 tools/qwen_tp8/frozen_tree_delay_pads.py $L/model_gen.json $L/gen_case/die.v $L/treedly $KO > $L/treedly.log 2>&1 || { log "TREE DELAY PADS FAIL $(tail -1 $L/treedly.log | cut -c1-400)"; exit 1; }
log "tree delay tiles: $(tail -1 $L/treedly.log | cut -c1-400)"
python3 tools/qwen_tp8/contract_v3_slots.py --case $L/gen_case --pads $L/treedly --out $L/case --baseline $BASE --checks $L/slot_checks.json > $L/slots.log 2>&1 || { log "POST-PASS FAIL $(tail -1 $L/slots.log | cut -c1-400)"; exit 1; }
log "post-pass: $(head -1 $L/slots.log | cut -c1-500)"
echo $SRC > $L/case/SOURCE_COMMIT; echo "--recipe $RC --pdn-rev r5 + tools/qwen_tp8/frozen_tree_delay_pads.py + tools/qwen_tp8/contract_v3_slots.py (results/physical/die_iter_1012/qwen_rom_tp8/scripts/it3_contract.sh)" > $L/case/SOURCE_NOTE
python3 tools/qwen_tp8/relay_ck_check.py $L/case/die.v > $L/relay_ck.log 2>&1; log "relay ck rc=$? $(cut -c1-200 $L/relay_ck.log)"
python3 tools/qwen_die_seam/tree_alignment.py --die-v $L/case/die.v --source "it3 case src $SRC" --out $L/tree_alignment.json > $L/tree_alignment.log 2>&1
log "tree alignment rc=$? $(python3 -c "import json;d=json.load(open('$L/tree_alignment.json'));print('misaligned',d.get('misaligned'),'nodes',d.get('nodes'))")"
nice python3 tools/hier_contract/derive_tp8.py --v5 results/arch/hier_contract_1011/qwen_rom.json --case $L/case --out $L/qwen_rom_tp8.json --version 3 --recipe tp8b --tile-cap M5 --prev $C \
  --slot-rev $L/case/SLOT_REV.json --change "${CHANGE:-slot revision 2026-10-13}" --source "tp8b it3 case (pdn r5 + tree delay tiles, src $SRC)" > $L/derive.log 2>&1; log "derive rc=$? $(tail -1 $L/derive.log | cut -c1-300)"
python3 -c "
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
d = Path('tools/hier_contract'); s = json.load(open(d / 'contract.schema.json'))
reg = Registry().with_resources([(p.name, Resource.from_contents(json.load(open(p)))) for p in d.glob('*.schema.json')])
c = json.load(open('$L/qwen_rom_tp8.json'))
e = list(Draft202012Validator(s, registry=reg).iter_errors(c))
print('schema', 'PASS' if not e else 'FAIL', len(c['slots']), 'slots', len(e), 'errors', [x.message[:120] for x in e[:3]]); sys.exit(1 if e else 0)" > $L/schema.log 2>&1; log "schema rc=$? $(tail -1 $L/schema.log)"
DW=$(sed -n 's/.*-die_area {0 0 \([0-9.]*\) .*/\1/p' $L/case/run.tcl | head -1); DH=$(sed -n "s/.*-die_area {0 0 [0-9.]* \([0-9.]*\)}.*/\1/p" $L/case/run.tcl | head -1)
nice python3 tools/qwen_kv_die/die_audit.py $L/case --die-w $DW --die-h $DH --out $L/audit.json > $L/audit.out 2>&1; log "die_audit rc=$? $(tail -1 $L/audit.out | cut -c1-260)"
nice python3 tools/die_top_lint.py lint --die qwen_rom --qwen-recipe $RC --out $L/lint > $L/lint.log 2>&1; log "lint $RC rc=$? $(tail -1 $L/lint.log | cut -c1-300)"

#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")/../../.."
P=physical/die_plan/qwen_compute
B=$P/bind
R=$B/phase2209
mkdir "$R"
O=run_phase2209
mkdir "$O"
probe=$B/asbuilt_phase_probe_2209.json
# Reprice changed physical fixed_cycles before any strict bind reads embedded lanes.
python3 tools/die_plan/gen.py latency "$P/die_plan_base_2209.json" --inplace --out "$O/pricing" > "$O/pricing.log" 2>&1
if [ -n "${QC_REUSE_ELAB:-}" ];then
 mkdir "$O/elab"
 cp "$QC_REUSE_ELAB/asbuilt.json" "$O/elab/asbuilt.json"
 cp "$QC_REUSE_ELAB/asbuilt_sources.json" "$O/elab/asbuilt_sources.json"
 printf '%s\n' "$QC_REUSE_ELAB" > "$O/elab_reused_map_only.txt"
else
 python3 tools/die_plan/bind.py elab "$P/die_plan_base_2209.json" --asbuilt "$probe" --out "$O/elab" --mem 64 > "$O/elab.log" 2>&1
fi
for d in probe base final;do
 mkdir "$O/$d"
 cp "$O/elab/asbuilt.json" "$O/$d/asbuilt.json"
 cp "$O/elab/asbuilt_sources.json" "$O/$d/asbuilt_sources.json"
done
ok() {
 python3 - "$1/bind_report.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print('BIND_STATUS',sys.argv[1],r['proof'],'splits',len(r.get('type_splits',[])),'errors',r['n_errors'])
assert r['n_errors']==0,r['errors'][:12]
for k in ('unbound','tied','undriven','multiply_bound'):assert r['proof'].get(k,0)==0,(k,r['proof'])
PY
}
python3 tools/die_plan/bind.py bind "$P/die_plan_base_2209.json" --asbuilt "$probe" --out "$O/probe" --strict > "$O/probe.log" 2>&1
ok "$O/probe"
python3 tools/die_plan/gen.py latency "$P/die_plan_base_2209.json" --groups "$O/probe/bus_groups.json" --out "$R/r8" > "$O/r8.log" 2>&1
python3 - <<'PY'
import json
from pathlib import Path
b=Path('physical/die_plan/qwen_compute/bind');r=json.load(open(b/'asbuilt_phase_probe_2209.json'));orig=json.load(open(b/'asbuilt_meth_fixed_su.json'));r.update(land_align='r8',param_regen=orig['param_regen'],land_r8=str(b/'phase2209/r8/qwen_compute_r8_landing.json'));(b/'asbuilt_phase_base_2209.json').write_text(json.dumps(r,indent=1)+'\n')
PY
python3 tools/die_plan/bind.py bind "$P/die_plan_base_2209.json" --asbuilt "$B/asbuilt_phase_base_2209.json" --out "$O/base" --strict > "$O/base.log" 2>&1
ok "$O/base"
python3 "$B/cb16_pads.py" --upstream "$O/base" "$R/r8/qwen_compute_r8_landing.json" "$R/dag_candidate.json" > "$O/dag.log" 2>&1
python3 "$P/apply_cb16_phase_types.py" --plan "$P/die_plan_base_2209.json" --r8 "$R/r8/qwen_compute_r8_landing.json" --overlay "$R/dag_candidate.json" --manifest "$R/phase_types.json" --out-plan "$P/die_plan_phase_fresh_2209.json" > "$O/phase.log" 2>&1
python3 - <<'PY'
import json
from pathlib import Path
p=Path('physical/die_plan/qwen_compute');b=p/'bind';r=json.load(open(b/'asbuilt_phase_base_2209.json'));r['land_r8_extra']=[str(b/'phase2209/dag_candidate.json')];r['internal_stations_types']=[c['type'] for c in json.load(open(b/'phase2209/phase_types.json'))['classes']];(b/'asbuilt_phase_final_2209.json').write_text(json.dumps(r,indent=1)+'\n')
from collections import Counter
epoch=Counter()
for member in json.load(open(b/'phase2209/dag_candidate.json'))['members']:epoch[member['sink_part']]+=member['tree_align']
old_epoch=Counter()
for member in json.load(open('results/rtl/qc_cb16_flow_1713/dag_candidate.json'))['members']:old_epoch[member['sink_part']]+=member['tree_align']
raw=json.load(open(p/'die_plan_phase_fresh_2209.json'));profiles=json.load(open(b/'phase2209/phase_types.json'));notes=json.load(open(p/'plan_notes.json'))
for c in profiles['classes']:
 old=next(x for x in json.load(open(p/'inputs/cb16_phase_profiles_1713.json'))['classes'] if x['type']==c['family'])
 base=notes['cells_per_type'][c['family']]['cells']-max(old['per_part_added_ff'][q]+old_epoch[q] for q in old['parts'])
 raw['partition_types'][c['type']]['cells']=base+max(c['per_part_added_ff'].values())
(p/'die_plan_phase_fresh_2209.json').write_text(json.dumps(raw,indent=1)+'\n')
print('FRESH_PHASE_SUMMARY',profiles['new_type_count'],profiles['logical_added_ff'],profiles['root_added_cycles_max'])
PY
python3 tools/die_plan/bind.py bind "$P/die_plan_phase_fresh_2209.json" --asbuilt "$B/asbuilt_phase_final_2209.json" --out "$O/final" --strict > "$O/final.log" 2>&1
ok "$O/final"
# Re-read the actual emitted bind ages: a correct overlay needs no further phase repair.
python3 "$B/cb16_pads.py" --upstream "$O/final" "$R/r8/qwen_compute_r8_landing.json" "$R/dag_final_check.json" > "$O/final_phase_check.log" 2>&1
python3 - "$R/dag_final_check.json" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]));assert r['summary']['members']==0,r['summary']
print('ACTUAL_FINAL_PHASE_FIXED_POINT_PASS',r['summary'])
CHECK
python3 tools/die_plan/regen_constants.py --die qwen_compute --bound "$O/final" --src-root . --out-json "$O/constants.json" > "$O/constants.log" 2>&1
cp "$R/dag_candidate.json" results/rtl/qc_cb16_flow_1713/dag_candidate.json
bash results/rtl/qc_cb16_flow_1713/run.sh > "$O/class_gate.log" 2>&1
printf 'QC_PHASE_BIND_AND_CLASS_PASS\n'

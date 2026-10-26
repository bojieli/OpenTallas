#!/usr/bin/env python3
"""Propose removal of an unbound constant-only plan link. Never adopt the candidate."""
import copy,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S,gen_phys,reset_tree as RT
raw=json.loads(subprocess.check_output(['git','show','HEAD:physical/die_plan/qwen_compute/die_plan.json'],cwd=ROOT))
old=S.Plan(copy.deepcopy(raw))
ls=[x for x in raw['lanes'] if re.fullmatch(r'sl_[EW][0-5]_st_a__flt',x['id'])]
assert len(ls)==12
pn={z for x in ls for z in x['ports']}; ports=[x for x in raw['ports'] if x['id'] in pn]; changes={}
for p in ports:
 for ep in ['src','dst']:
  part=p[ep]['part'];t=old.parts[part]['type'];b=p[ep]['bus'];changes[t]=b
assert len(changes)==10
for t,b in changes.items():
 before=raw['partition_types'][t]['buses'];raw['partition_types'][t]['buses']=[x for x in before if x['name']!=b];assert len(before)-len(raw['partition_types'][t]['buses'])==1
raw['lanes']=[x for x in raw['lanes'] if x not in ls];raw['ports']=[x for x in raw['ports'] if x['id'] not in pn]
removed_age={x['id']:raw['latency']['lanes'].pop(x['id']) for x in ls}
new=S.Plan(raw);invariants={}
for t,b in changes.items():
 keep=[x for x in gen_phys.type_pins(old,t) if x[0]!=b]
 invariants[t]={'remaining_data_pins_identical':keep==gen_phys.type_pins(new,t),'clock_reset_pins_identical':gen_phys.tap_pins(old,t)==gen_phys.tap_pins(new,t),'reset_tree_identical':RT.for_type(old,t)==RT.for_type(new,t)}
assert all(all(v.values()) for v in invariants.values())
report={'status':'PROPOSED_NOT_ADOPTED_INTERFACE_DELTA','id':'D-QC-DEAD-FAULT','removed_buses':changes,'removed_lanes':ls,'removed_ports':ports,'obsolete_plan_ages_removed':removed_age,'physical_effect':'48 endpoint pins and24 phantom wire bits removed across12slice pairs; no actual bound logic','added_hardware_cycles':0,'token_model':'Do not subtract obsolete constant-only lane ages from functional schedule; existing actual fault path remains STM -> FW','invariants':invariants,'schema_errors':S.validate(raw),'evidence':'All4 ST-a kit_rtl.json plan_buses_unbound flt_o/spare_out_bits2; actual wrappers assign flt_o=2d0. All6FW kit_rtl.json plan_buses_unbound flt_st_a_i; bound modules lack that input. Real STM->FW fault link retained.'}
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);(out/'proposal.json').write_text(json.dumps(report,indent=2)+'\n');(out/'candidate_plan.json').write_text(json.dumps(raw,indent=1)+'\n');print(json.dumps(report,indent=2))

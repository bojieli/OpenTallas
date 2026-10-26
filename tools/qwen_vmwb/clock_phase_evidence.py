#!/usr/bin/env python3
"""Join reported immutable insertion references without inventing missing leaf R."""
import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'results/arch/qwen_vm_residual_1015';x=json.loads((D/'partitioned_parent_clock_ledger/actual_parent_ledger.json').read_text());inventory=json.loads((D/'physical_inventory/inventory.json').read_text())['inventory'];cache={}
def insertion(path):
 if path in cache:return cache[path]
 try:b=subprocess.check_output(['git','show','HEAD:'+path],cwd=R,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError:return None
 data=json.loads(b);cache[path]=(data,hashlib.sha256(b).hexdigest());return cache[path]
for row in x['clock_endpoints']:
 cls=row['master'];view=inventory.get(cls);row['required_phase']='phi - exact source/view R_tt for this entry';row['R_tt_qualified_ps']=None
 if not view:
  row['phase_status']='New standard master has no physical insertion view; phase remains OPEN';continue
 path=str(Path(view['lef']).with_name('insertion.json'));found=insertion(path)
 if not found:row['phase_status']='Insertion view missing; phase OPEN';continue
 data,sha=found;entry=(data.get('clock_measurements') or {}).get(row['pin'],data);raw=entry.get('env',{}).get('CK_TT_MEAN');row['reported_view_R_tt_ps']=raw;row['insertion_source']=path;row['insertion_sha256']=sha;row['phase_status']='Reported immutable view reference only; exact source/view and nested clock composition must be qualified before delivery'
 if cls.startswith('qvm_') and row['pin'].startswith(('ck_in','ck_out','ck_cap','ck_ctrl')):
  child='qvm_data256_native' if row['pin']!='ck_ctrl' else ('qvm_su_bank_ctrl_native' if cls=='qvm_su_bank_native' else 'qvm_bank_ctrl_native')
  cp=f'physical/ref_tile/{child}/views/{child}/insertion.json';ci=insertion(cp)
  if ci:
   cd,ch=ci;cr=cd.get('env',{}).get('CK_TT_MEAN');row['nested_child_reference']={'master':child,'source':cp,'sha256':ch,'reported_R_tt_ps':cr,'unqualified_sum_with_parent_ps':raw+cr if isinstance(raw,(int,float)) and isinstance(cr,(int,float)) else None};row['phase_status']='Parent reference reaches hard-child clock pin; nested child R is separately reported. Additive composition is a candidate requiring explicit review, not inherited qualification.'
x['phase_status']='Logical connectivity PASS. Physical phase delivery remains OPEN until exact source/view qualification and nested clock reference composition.'
x['parent_residual_phase']={'port':'ck','source_FF_bits':x['source_ff_bits_by_parent_clock'].get('ck'),'R_tt_qualified_ps':None,'status':'Unhardened source root exceeds15k; partition into real leaves before phase/timing qualification'}
(D/'partitioned_parent_clock_ledger/phase_evidence.json').write_text(json.dumps(x,indent=2)+'\n')
print({'endpoints':len(x['clock_endpoints']),'raw_insertion_references':sum('reported_view_R_tt_ps' in r for r in x['clock_endpoints']),'phase_qualified':sum(r['R_tt_qualified_ps'] is not None for r in x['clock_endpoints']),'residual':x['parent_residual_phase']})

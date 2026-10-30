#!/usr/bin/env python3
"""Prepare, never adopt, four fixed-parameter current-native query aliases.

Input is the hierarchical blackbox compose cache, not an elaborated RTL design.
The named views are backed by direct-wire RTL wrappers with fixed native RT.
"""
import argparse,copy,json,pathlib
ROLES={'NE':('NE_hub','u_hb_idx__op_Q__q1',171),'NW':('NW_hub','u_hb_idx__op_Q__q1',173),'SE':('NE_hub','u_hb_idx__op_Q__q0',171),'SW':('NW_hub','u_hb_idx__op_Q__q0',171)}
BASE='ot_hbm_idx_vm_query_static_n12'
def prepare(original):
 d=dict(original);d['modules']=dict(original['modules']);native_top=original['modules']['hbm_current_native_top'];top=dict(native_top);top['cells']=dict(native_top['cells']);d['modules']['hbm_current_native_top']=top;base=d['modules'][BASE];manifest=[]
 assert len(base['ports'])==16
 for q,(part,inst,rt) in ROLES.items():
  key='hb_idx__op_'+q;c=copy.deepcopy(top['cells'][key]);top['cells'][key]=c
  assert c['type']==BASE,(key,c['type'])
  assert set(c['parameters'])=={'VM_RT_EXTRA'},(key,c['parameters'])
  assert int(c['parameters']['VM_RT_EXTRA'],2)==rt,(key,'wrong native calendar')
  assert set(c['connections'])==set(base['ports']),(key,'port mismatch')
  for p,v in base['ports'].items():assert len(c['connections'][p])==len(v['bits']),(key,p)
  alias=BASE+'__rt'+str(rt)
  if alias not in d['modules']:
   m=copy.deepcopy(base);m['parameter_default_values']={};m.setdefault('attributes',{})['hdlname']=alias;d['modules'][alias]=m
  c['type']=alias;c['parameters']={}
  manifest.append(dict(native_instance=key,part=part,plan_instance=inst,master=alias,VM_RT_EXTRA=rt,added_cycles=0))
 # Every unselected module/cell is the original object; selected cells differ
 # only in type and the one fixed parameter, preserving every connection bit.
 assert set(d)==set(original)
 assert set(top)==set(native_top)
 for key,c in top['cells'].items():
  old=native_top['cells'][key]
  if key in {'hb_idx__op_'+q for q in ROLES}:
   restored=dict(c);restored['type']=old['type'];restored['parameters']=old['parameters']
   assert restored==old,'undeclared compose cell mutation'
  else:assert c is old
 for key,m in original['modules'].items():
  if key!='hbm_current_native_top':assert d['modules'][key] is m
 return d,manifest
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input');ap.add_argument('output');a=ap.parse_args()
 original=json.load(open(a.input));d,m=prepare(original)
 for row in m:
  cell=original['modules']['hbm_current_native_top']['cells'][row['native_instance']]
  prior=cell['parameters']['VM_RT_EXTRA']
  cell['parameters']['VM_RT_EXTRA']=format(173 if row['VM_RT_EXTRA']==171 else 171,'032b')
  try:prepare(original)
  except AssertionError:pass
  else:raise AssertionError('wrong-RT mutant accepted')
  finally:cell['parameters']['VM_RT_EXTRA']=prior
 pathlib.Path(a.output).write_text(json.dumps(d,separators=(',',':'))+'\n')
 pathlib.Path(a.output+'.manifest.json').write_text(json.dumps({'status':'SOURCE_PREPARATION_ONLY_UNADOPTED','generic_view':'be0b530febe5 HOLD','roles':m,'exact_reversible_mutation':True,'wrong_rt_mutants_rejected':4},indent=2)+'\n')
 print('PASS: four exact native roles, 16 ports each, reversible aliases, four wrong-RT mutants rejected')

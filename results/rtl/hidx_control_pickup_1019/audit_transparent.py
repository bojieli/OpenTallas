#!/usr/bin/env python3
"""Diagnostic only: strict scalar refusal preserved; explicit macro-bus expansion."""
import collections,gzip,hashlib,json,pathlib,sys
import safe_source_contract as S
from dft.liberty import _parse_groups,_read_text,_strip_heavy
r=pathlib.Path(__file__).resolve().parent
libs=[r/'census'/f'{n}.lib' for n in ['AO','OA','SIMPLE','INVBUF','SEQ']]
mp=r/'census/ot_hbm_idx_topk_link_static_p/mapped.json'
net=json.loads(mp.read_text());top='ot_hbm_idx_topk_link_static_p';mod=net['modules'][top]
used={c['type'] for c in mod['cells'].values()}
try:
 S.native_cells(libs+[r/'macro_tt.lib'],used_masters=used)
 strict={'verdict':'UNEXPECTED_ACCEPT'}
except S.ContractError as e: strict={'verdict':'REFUSED','error':str(e)}
(r/'strict_native_refusal.json').write_text(json.dumps(strict,indent=2)+'\n')
library=S.native_cells(libs,used_masters=used)
root=_parse_groups(_strip_heavy(_read_text(r/'macro_tt.lib')))
lib=[b for k,a,b in root['groups'] if k=='library'][0]
types={a[0]:b['attrs'] for k,a,b in lib['groups'] if k=='type'}
cs=[(a[0],b) for k,a,b in lib['groups'] if k=='cell'];assert len(cs)==1
master,body=cs[0];pins={};buswidth={}
for kind,args,body in body['groups']:
 if kind not in ('pin','bus'):continue
 a=body['attrs'];direction=a['direction'];assert direction in ('input','output')
 names=args
 if kind=='bus':
  t=types[a['bus_type']];hi=int(t['bit_from']);lo=int(t['bit_to']);width=int(t['bit_width']);assert lo==0 and hi==width-1
  buswidth[args[0]]=width;names=[f'{args[0]}[{i}]' for i in range(width)]
 for name in names:
  pins[name]={'direction':direction,'clock':a.get('clock')=='true','function':None,'role':'clock' if a.get('clock')=='true' else 'data','native_capacitance':{k:a[k] for k in ('capacitance','rise_capacitance','fall_capacitance') if k in a},'capacitance_unit':lib['attrs'].get('capacitive_load_unit')}
library[master]={'pins':pins,'role':'macro','transparent':None}
for name,c in mod['cells'].items():
 if c['type']!=master:continue
 con={};dirs={}
 for pn,bits in c['connections'].items():
  if pn in buswidth:
   assert len(bits)==buswidth[pn]
   for i,bit in enumerate(bits):con[f'{pn}[{i}]']=[bit];dirs[f'{pn}[{i}]']=c['port_directions'][pn]
  else:con[pn]=bits;dirs[pn]=c['port_directions'][pn]
 assert set(con)==set(pins)
 c['connections']=con;c['port_directions']=dirs
out=S.census(net,top,library)
out['diagnostic_scope']='Native strict REFUSED bus; independently expanded exact native macro buses for diagnosis only, not production qualification'
out['provenance']={'mapped_sha256':S.sha(mp),'libraries':{str(p):S.sha(p) for p in libs+[r/'macro_tt.lib']},'audit_sha256':S.sha(__file__),'strict_native':strict}
with gzip.open(r/'transparent_diagnostic.json.gz','wt') as f:json.dump(out,f)
summary={k:v for k,v in out.items() if k not in ('drivers','input_registration','output_ownership','disconnected_outputs')}
summary['worst']=sorted(out['drivers'],key=lambda x:x['loads'],reverse=True)[:30]
summary['max_by_role']={role:max(x['loads'] for x in out['drivers'] if x['role']==role) for role in set(x['role'] for x in out['drivers'])}
summary['violations_by_role']=dict(collections.Counter(x['role'] for x in out['drivers'] if x['loads']>32 and not x['driver'].startswith('literal:')))
summary['unregistered_inputs']=[x for x in out['input_registration'] if not x['registered_data_endpoints_only'] and x['endpoint_roles'].get('data',0)]
summary['non_ff_outputs']=[x for x in out['output_ownership'] if not x['registered']]
(r/'transparent_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k in ('verdict','max_by_role','violations_by_role','counts','max_nonliteral_loads','diagnostic_scope','provenance')},indent=2))

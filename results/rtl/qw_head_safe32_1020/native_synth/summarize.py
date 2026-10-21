import json,collections,re,os
from pathlib import Path
p=Path('safe32_native_synth_out')/os.environ.get('MAPPED_TAG','safe32r5b')/'work/orfs';m=json.loads((p/'flat.json').read_text())['modules']['ot_qfd_tt_ctlm_static_hr_safe32_native32'];r=json.loads((p/'native_census_current.json').read_text())
bybit=collections.defaultdict(list)
for n,d in m['netnames'].items():
 for b in d['bits']:bybit[b].append(n)
cs=m['cells'];viol=[]
for v in r['violations']:
 bit=m['netnames'].get(v['net'],{}).get('bits',[])
 c=cs.get(v['driver'].rsplit('/',1)[0],{})
 viol.append(dict(driver=v['driver'],type=c.get('type'),role=v['driver_role'],loads=v['loads'],aliases=sorted(set(n for b in bit for n in bybit[b]))))
ff=[(n,c)for n,c in cs.items()if c['type'].startswith(('DFF','SDFF'))];mac=[(n,c['type'])for n,c in cs.items()if c['type'].startswith('ot_sram')]
out=dict(status=r['status'],cells=len(cs),flops=len(ff),macros=mac,roots=r['roots_examined'],max=r['max_dynamic_loads'],violations=sorted(viol,key=lambda x:x['loads'],reverse=True),kept_q_netnames=sum(n.startswith('safe32_')for n in m['netnames']),unregistered_output_bits=[],input_pin_loads=[])
roles=json.loads((p/'liberty_roles.json').read_text())['roles']
qbits={b for c in cs.values()if roles[c['type']]['sequential'] for pn,bs in c['connections'].items()if c['port_directions'][pn]=='output'for b in bs}
transparent=[]
for c in cs.values():
 role=roles[c['type']]
 inputs=[(pn,bs)for pn,bs in c['connections'].items()if c['port_directions'][pn]=='input'and not any(v['clock']for k,v in role['pins'].items()if k==pn)]
 outputs=[(pn,bs)for pn,bs in c['connections'].items()if c['port_directions'][pn]=='output']
 if not role['sequential']and len(inputs)==len(outputs)==1 and len(inputs[0][1])==len(outputs[0][1])==1:
  func=re.sub(r'[\s()]','',role['pins'][outputs[0][0]].get('function')or'')
  pin=inputs[0][0]
  if func in (pin,'!'+pin,'~'+pin,pin+chr(39)):transparent.append((inputs[0][1][0],outputs[0][1][0]))
while True:
 old=len(qbits)
 for a,b in transparent:
  if a in qbits:qbits.add(b)
 if len(qbits)==old:break
out['pin_inventory_scope']='actual sequential cell outputs through actual Liberty unary BUF/INV; constants excluded; no geometry/timing claim'
for n,v in m['ports'].items():
 if v['direction']=='output':
  missing=[i for i,b in enumerate(v['bits'])if isinstance(b,int) and b not in qbits]
  if missing:out['unregistered_output_bits'].append(dict(port=n,bits=missing))
(p/'source_summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items()if k!='violations'},indent=2));print(json.dumps(out['violations'][:25],indent=2))

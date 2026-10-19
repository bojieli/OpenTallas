"""Inspect mapped useful hierarchy, independently of naming in the flat census."""
import json,collections
from pathlib import Path
j=json.loads(Path('out/hierarchical.json').read_text())['modules']
counts=collections.Counter(); leaves=[]; trees=[]
def attrnum(x):
 try:return int(x,2)
 except (ValueError,TypeError):return x

def walk(mod,path):
 m=j[mod];name=m.get('attributes',{}).get('hdlname','')
 for n,c in m.get('cells',{}).items():
  t=c['type'];p=path+'/'+n
  if t in j and not j[t].get('attributes',{}).get('blackbox'):
   original=j[t].get('attributes',{}).get('hdlname','')
   if original in ('hidx_csa','hidx_csa_fa','hidx_csa_ha'):
    counts[original]+=1
    row=dict(path=p,module=t,kind=original,parameters={k:attrnum(v) for k,v in j[t].get('parameter_default_values',{}).items()},cells=dict(collections.Counter(x['type'] for x in j[t]['cells'].values())),ports=j[t]['ports'])
    (trees if original=='hidx_csa' else leaves).append(row)
   walk(t,p)
walk('hidx_coupon1','hidx_coupon1')
assert counts==dict(hidx_csa=36,hidx_csa_fa=312,hidx_csa_ha=132),counts
native=json.loads(Path('out/native.json').read_text())
count_outputs=[]; mask_outputs=[]
for r in native['all_roots']:
 a=r['aliases']
 if any('.count0[' in x or '.count1[' in x for x in a):
  # Include native count roots behind transparent aliases through endpoint ownership.
  ds=[x for x in r['endpoints'] if x['kind']=='ff' and x['role']=='data']
  if ds:count_outputs.append(dict(driver=r['name'],master=r['master'],loads=r['loads'],cap=r['cap'],real_selector_d=len(ds),aliases=a,endpoints=r['endpoints']))
 if r['kind']=='ff' and any('.mask[' in x for x in a):mask_outputs.append(dict(driver=r['name'],loads=r['loads'],cap=r['cap'],aliases=a))
assert len(count_outputs)==168,(len(count_outputs),'12 pc8 *4 +24pc16*5')
assert all(x['real_selector_d']==12 and x['loads']==12 for x in count_outputs)
assert native['summary']['ff']==2616
assert native['summary']['clock_contacts']==2616
assert native['summary']['constant_endpoints']=={}
Path('out/csa_audit.json').write_text(json.dumps(dict(hierarchy_counts=dict(counts),trees=trees,arithmetic_leaves=leaves,count_outputs=count_outputs,mask_outputs=mask_outputs),indent=2)+'\n')
print(json.dumps(dict(hierarchy_counts=dict(counts),count_outputs=len(count_outputs),selector_d=12,mask_ff_roots=len(mask_outputs),mask_max=max(x['loads'] for x in mask_outputs),ff=2616,constants=0)))

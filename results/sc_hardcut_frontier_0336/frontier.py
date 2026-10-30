import re,json,collections,sys
from pathlib import Path
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/sc-hardcut-review-0336/sc_cap_child_0336/source/rtl/qfd_dv_s5_sc2_k79.sv');s=p.read_text()
ports={m.group(3):{'direction':m.group(1),'width':int(m.group(2))+1} for m in re.finditer(r'(input|output) wire \[(\d+):0\] (\w+);',s)}
assigns=re.findall(r'assign\s+(.*?)\s*=\s*(.*?);',s);deps={};inputs={};outputs={};drivers={};ff={};cons=collections.defaultdict(list)
for lhs,rhs in assigns:
 if rhs in ports and ports[rhs]['direction']=='input':
  ns=re.findall(r'n_\d+',lhs)
  for bit,n in enumerate(reversed(ns)):inputs[n]=f'{rhs}[{bit}]'
 elif lhs in ports and ports[lhs]['direction']=='output':
  for bit,n in enumerate(reversed(re.findall(r'n_\d+',rhs))):outputs[f'{lhs}[{bit}]']=n
 elif re.fullmatch(r'n_\d+',lhs):
  deps[lhs]=re.findall(r'n_\d+',rhs);drivers[lhs]={'type':'assign','expression':rhs}
for typ,inst,pins in re.findall(r'\b(qfd_s2_bmath_\w+)\s+#\(\.ID\(\d+\)\)\s+(\w+)\(([^;]+)\);',s):
 ps=dict(re.findall(r'\.(\w+)\(([^()]*)\)',pins));out=ps.get('Q',ps.get('Y'));assert out
 drivers[out]={'type':typ,'instance':inst,'pins':ps}
 if '_dff_' in typ:ff[out]=drivers[out];continue
 deps[out]=[v for k,v in ps.items() if k not in ('Q','Y') and re.fullmatch(r'n_\d+',v)]
for out,ds in deps.items():
 for d in ds:cons[d].append(out)
for out,f in ff.items():
 for pin in ('D',):
  d=f['pins'][pin]
  if d.startswith('n_'):cons[d].append(('FF',f['instance'],pin))
from functools import lru_cache
@lru_cache(None)
def back(n):
 if n in ff:return {'ff':{ff[n]['instance']},'input':set(),'depth':0,'unknown':set()}
 if n in inputs:return {'ff':set(),'input':{inputs[n]},'depth':0,'unknown':set()}
 if n not in deps:return {'ff':set(),'input':set(),'depth':0,'unknown':{n}}
 vs=[back(d) for d in deps[n]]
 return {'ff':set().union(*(v['ff']for v in vs)),'input':set().union(*(v['input']for v in vs)),'depth':1+max((v['depth']for v in vs),default=-1),'unknown':set().union(*(v['unknown']for v in vs))}
outs={}
for port,n in outputs.items():
 a=back(n);outs[port]={'net':n,'direct_ff':n in ff,'first_driver':drivers.get(n),'max_combo_depth_to_ff_or_input':a['depth'],'source_ff_count':len(a['ff']),'input_bypass':sorted(a['input']),'unknown':sorted(a['unknown'])}
summary={}
for name,port in ports.items():
 if port['direction']=='output':
  os=[v for k,v in outs.items()if k.startswith(name+'[')];summary[name]={'bits':len(os),'direct_ff_bits':sum(v['direct_ff']for v in os),'max_combo_depth':max(v['max_combo_depth_to_ff_or_input']for v in os),'bypass_bits':sum(bool(v['input_bypass'])for v in os),'max_source_ff_count':max(v['source_ff_count']for v in os)}
ins={}
for n,name in inputs.items():
 if name.startswith(('ck[','rst_n[')):continue
 cs=cons[n];ins[name]={'net':n,'immediate_data_ff_sinks':[v[1]for v in cs if isinstance(v,tuple)],'immediate_comb_sinks':[v for v in cs if isinstance(v,str)]}
report={'scope':'source structural frontier, helper/assign combo levels; not mapped timing','state_ff_helpers':len(ff),'outputs_summary':summary,'outputs':outs,'inputs':ins,'shared_input_bits':[k for k,v in ins.items() if len(v['immediate_data_ff_sinks'])!=1],'input_fanout_histogram':dict(collections.Counter(len(v['immediate_data_ff_sinks'])for v in ins.values()))}
(Path(sys.argv[2]) if len(sys.argv)>2 else Path('/home/ubuntu/sc-hardcut-review-0336/frontier.json')).write_text(json.dumps(report,indent=1))
print(json.dumps({'state_ff_helpers':len(ff),'outputs_summary':summary,'input_bits':len(ins),'input_bits_with_comb_sinks':sum(bool(v['immediate_comb_sinks'])for v in ins.values()),'input_bits_with_direct_ff_sinks':sum(bool(v['immediate_data_ff_sinks'])for v in ins.values())},indent=2))

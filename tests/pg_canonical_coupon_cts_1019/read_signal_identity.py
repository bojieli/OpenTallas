from pathlib import Path
import json,sys,collections
root=Path.cwd();p=root/'output/default/analysis';sys.path.insert(0,str(root/'tools/closure_loop'));import safe_source_contract as S
old=json.loads((root/'tests/pg_canonical_coupon_1019/evidence_native_v3/raw.json').read_text());new=json.loads((p/'raw.json').read_text());top='ot_pg_canonical_xor16_1019'
used={c['type'] for raw in (old,new) for c in raw['modules'][top]['cells'].values() if any(v not in ('POWER','GROUND') for v in c['pin_signal_types'].values())}
libs=[p/'libs'/n for n in ['asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz','asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz']];native=S.native_cells(libs,used_masters=used)
def graph(raw):
 m=raw['modules'][top];drivers={};core={};clock_drivers=[]
 def add(bit,expr):
  assert bit not in drivers,('multiple drivers',bit)
  drivers[bit]=expr
 for n,t in m['ports'].items():
  if t['direction']=='input' and t['signal_type'] not in ('POWER','GROUND'):add(t['bits'][0],('port',n))
 for n,c in m['cells'].items():
  if c['type'] not in native:continue
  lib=native[c['type']]
  if lib['role']=='ff' or not lib['transparent'] and lib['role']!='static':core[n]=(c['type'],lib)
  for pin,bs in c['connections'].items():
   if c['port_directions'][pin]!='output' or not bs or c['pin_signal_types'][pin] in ('POWER','GROUND'):continue
   if lib['transparent']:
    i,o,pol=lib['transparent'];add(bs[0],('transparent',c['connections'][i][0],pol))
   elif lib['role']=='static':add(bs[0],('constant',lib['pins'][pin]['function']))
   else:add(bs[0],('cell',n,pin))
 def resolve(bit,seen=frozenset()):
  assert bit not in seen,('cycle',bit)
  e=drivers[bit]
  if e[0]!='transparent':return e,0
  r,pol=resolve(e[1],seen|{bit});return r,pol^e[2]
 loads={}
 for n in core:
  c=m['cells'][n]
  for pin,bs in c['connections'].items():
   if c['port_directions'][pin]=='input' and c['pin_signal_types'][pin] not in ('POWER','GROUND'):loads[(n,pin)]=resolve(bs[0])
 for n,t in m['ports'].items():
  if t['direction']=='output' and t['signal_type'] not in ('POWER','GROUND'):loads[('port',n)]=resolve(t['bits'][0])
 for bit,net in m['net_metadata'].items():
  if net['signal_type']!='CLOCK':continue
  owners=[];sinks=[]
  for n,c in m['cells'].items():
   if c['type'] not in native:continue
   for pin,bs in c['connections'].items():
    if bs==[int(bit)] and c['pin_signal_types'][pin] not in ('POWER','GROUND'):(owners if c['port_directions'][pin]=='output' else sinks).append((n,pin,c['type']))
  clock_drivers.append({'net':net['name'],'drivers':owners,'sinks':sinks,'direct_loads':len(sinks)})
 return core,loads,clock_drivers
a,b=graph(old),graph(new);assert a[0]==b[0],('state/logic/native function change',set(a[0])^set(b[0]));assert a[1]==b[1],[(k,a[1].get(k),b[1].get(k)) for k in a[1].keys()|b[1].keys() if a[1].get(k)!=b[1].get(k)]
result={'verdict':'PASS','scope':'Exact native nontransparent cell/master/function identities plus all core input/output source and inversion parity relationships through actual native BUF/INV and ties. This is a netlist structural correspondence, not a formal RTL equivalence proof.','nontransparent_state_and_logic_cells':len(a[0]),'all_core_and_port_relationships':len(a[1]),'source_FF_count':sum(v[1]['role']=='ff' for v in b[0].values()),'new_state_or_changed_nontransparent_functions':0,'clock_net_count':len(b[2]),'maximum_direct_clock_driver_loads':max(t['direct_loads'] for t in b[2]),'all_native_clock_net_drivers':b[2]}
(p/'signal_identity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='all_native_clock_net_drivers'}))

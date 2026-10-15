#!/usr/bin/env python3
import collections,hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent;q=p/'s81_static_collective_slab.generic.json';j=json.loads(q.read_text());top='s81_static_collective_slab';m=j['modules'][top]
rootbits={}
for name in ['ck_control','ck_lane','ck_hc_lane']:
 for i,b in enumerate(m['ports'][name]['bits']):rootbits[b]=f'{name}[{i}]'
counts=collections.Counter();types=collections.defaultdict(collections.Counter);unresolved=[];macros=[]
def walk(module,path,mapping):
 for name,cell in j['modules'][module]['cells'].items():
  t=cell['type'];cn=cell['connections'];here=path+'.'+name
  def resolve(bit):return mapping.get(bit,('internal',path,bit)) if isinstance(bit,int) else bit
  if t in j['modules'] and not j['modules'][t].get('attributes',{}).get('blackbox'):
   child={}
   for port,defn in j['modules'][t]['ports'].items():
    for internal,external in zip(defn['bits'],cn[port]):child[internal]=resolve(external)
   walk(t,here,child)
  elif t.startswith(('$_DFF','$_SDFF')):
   clock=resolve(cn['C'][0]);root=rootbits.get(clock)
   if root:counts[root]+=len(cn['Q']);types[root][t]+=len(cn['Q'])
   else:unresolved.append(dict(cell=here,type=t,clock=clock))
  elif t=='ot_rom_4096x266_m8':macros.append(dict(instance=here,master=t,clock=rootbits.get(resolve(cn['clk'][0])),internal_register_count='hard macro excluded'))
  elif t.startswith(('$_DLATCH','$mem')):unresolved.append(dict(cell=here,type=t))
walk(top,top,{b:b for port in m['ports'].values() for b in port['bits'] if isinstance(b,int)})
assert len(counts)==29 and not unresolved,(len(counts),unresolved[:10])
r=dict(schema='s81.actual-collective-clock-root-census.v1',source_commit='2eb33e9a8e8046d4f579fc1395e0ac6038a11341',top=top,parameters=dict(ROM_FILE='',CYCLES=1,MUT=0,VMB_PINCAP=1),scope='Current parent-default source elaboration. SYNTHESIS ROM interface is a hard blackbox, not modeled storage. Counts are generic one-bit sequential cell clock sinks, before technology mapping/CTS. Wrapper reset_q adds two control0 flops outside this slab.',root_count=len(counts),slab_sequential_clock_sinks=sum(counts.values()),wrapper_additional_sinks={'ck_control[0]':2},full_wrapper_delivered_root_sequential_sinks=sum(counts.values())+2,per_root=[dict(clock=k,sequential_clock_sinks=counts[k],cell_types=dict(types[k])) for k in rootbits.values()],hard_macros=macros,unresolved_clock_sinks=unresolved,raw_json_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),tool='Yosys0.67 2d1509d1b',peak_memory_mb=4862.31,elapsed_yosys_seconds=86.84,warning='Not a production calendar7 root census; candidate needs35 roots. CYCLES1 is actual default; a different production parameter changes calendar storage. This is not placed CTS load capacitance or an outline proof.')
(p/'root_census29.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['root_count','slab_sequential_clock_sinks','full_wrapper_delivered_root_sequential_sinks']}));print('\n'.join(f'{k}: {v}' for k,v in counts.items()))

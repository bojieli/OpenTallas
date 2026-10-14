#!/usr/bin/env python3
"""Census the actual elaborated/optimized hardened-parent JSON, preserving root identity."""
import sys,json,collections,hashlib,pathlib
p=pathlib.Path(sys.argv[1]);d=json.loads(p.read_text());top='ot_hbm_native_fence_clocked_1014';mods=d['modules'];m=mods[top]
roots={b:f'{n}[{i}]' if len(v['bits'])>1 else n for n,v in m['ports'].items() for i,b in enumerate(v['bits'])}
count=collections.Counter();banks=[]
def walk(name,bindings,path):
 for inst,c in mods[name].get('cells',{}).items():
  typ=c['type'];conn={n:[bindings.get(b,(path,b)) for b in bs] for n,bs in c['connections'].items()}
  if typ.startswith('ot_hbm_native_fence_bank'):
   clock=conn['clk'][0];banks.append({'instance':path+'/'+inst,'master':typ,'clock':roots.get(clock,str(clock)),'clock_id':clock});continue
  if typ in mods and not mods[typ].get('attributes',{}).get('blackbox'):
   bind={b:x for n,v in mods[typ]['ports'].items() for b,x in zip(v['bits'],conn[n])};walk(typ,bind,path+'/'+inst)
  elif typ in ['$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$dffsr','$dffsre','$aldff','$aldffe']:
   clock=conn['CLK'][0];count[roots.get(clock,str(clock))]+=int(c['parameters']['WIDTH'],2)
walk(top,{b:b for v in m['ports'].values() for b in v['bits']},top)
by=collections.Counter(b['master'] for b in banks);clock_ids=[b['clock_id'] for b in banks]
r={'schema':'opentallas.fence.actual_hardparent_census.v1','source_json_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':'actual Yosys proc/flatten/opt/memory_map/opt hardchild elaboration; notroutedCTS/mappedASICview','top':top,'params':{'PINRET':1,'INPIN':1,'HOLDBUF':2},'own_ff_by_clock':dict(count),'own_ff_total':sum(count.values()),'actual_hardchildren':len(banks),'hardchild_counts':dict(by),'unique_child_clock_nets':len(set(clock_ids)),'child_clocks_alias':len(set(clock_ids))!=len(clock_ids),'declared_child_clock_ports':165,'unused_declared_clock_indices':[i for i in range(165) if f'bank_clks[{i}]' not in {b['clock'] for b in banks}],'reason_164_vs_estimate_165':'u_ack FIFO data isconstant0 andout_data unused. Optimizer correctly removesitsbank1storage/readselect/writecopy; ackvalid/control staysparent. Do notadddummystate orforcekeep toclaim165activeroots. Bank1separatestandaloneview remainsdistinctrequestedfamilyartifact.','children':banks,'physical_acceptance':False}
assert r['actual_hardchildren']==164 and r['unique_child_clock_nets']==164 and not r['child_clocks_alias']
assert set(count)=={'clk'} and sum(count.values())<=15000
pathlib.Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n');print({k:r[k] for k in ['own_ff_by_clock','actual_hardchildren','hardchild_counts','unique_child_clock_nets','unused_declared_clock_indices']})

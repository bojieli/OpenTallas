#!/usr/bin/env python3
"""Recursive primitive pin-load census of a Yosys-mapped JSON, with aliases unified.
Counts all data/reset/enable sinks and excludes only the named root clock net.
Generic ABC-mapped measurement; technology-specific native mapping still required.
"""
import json,sys,collections,re
x=json.load(open(sys.argv[1]));top=sys.argv[2];mods=x['modules'];loads=collections.Counter();drivers={};names={};clocks=set();leaves=0;celltypes=collections.Counter();control_aliases={};buf_inputs={};buf_outputs={};sinks=collections.defaultdict(list)

def visit(mod,path,portmap=None):
 global leaves
 m=mods[mod];mapping={}
 if portmap:
  for n,p in m['ports'].items():
   for b,v in zip(p['bits'],portmap[n]):mapping[b]=v
 def bit(b):
  if isinstance(b,str):return b
  return mapping.get(b,(path,b))
 for n,p in m.get('netnames',{}).items():
  for i,b in enumerate(p['bits']):
   full=f'{path}.{n}[{i}]'; key=bit(b)
   if key not in names or ('$' in names[key] and '$' not in full):names[key]=full
   if re.search(r'(?:\.|/)(?:rq|warm|wc|rc|read_oh|write_oh)\[',full):control_aliases[full]=key
 if path==top:
  
  for clock_name in ('ck_w','ck_r'):
   clocks.update(bit(b) for b in m['ports'][clock_name]['bits'])
 for n,c in m['cells'].items():
  conn={p:[bit(b) for b in bs] for p,bs in c['connections'].items()}
  if c['type'] in mods and not int(mods[c['type']].get('attributes',{}).get('blackbox','0'),2):
   visit(c['type'],path+'/'+n,conn)
  else:
   leaves+=1;celltypes[c['type']]+=1
   isbuf=c['type'].startswith(('BUF','INV'))
   if isbuf:
    ins=[b for p,bs in conn.items() if c['port_directions'][p]=='input' for b in bs]
    outs=[b for p,bs in conn.items() if c['port_directions'][p]=='output' for b in bs]
    if len(ins)==1 and len(outs)==1:
     buf_inputs[outs[0]]=ins[0];buf_outputs[path+'/'+n]=outs[0]
   for p,bs in conn.items():
    direction=c['port_directions'][p]
    for b in bs:
     if isinstance(b,str) or b in clocks:continue
     if direction=='input':
      loads[b]+=1;sinks[b].append((path+'/'+n+'/'+p,path+'/'+n if isbuf else None))
     if direction=='output':drivers[b]=path+'/'+n+'/'+p
visit(top,top)
def terminal_sinks(b,seen=None):
 seen=set() if seen is None else seen
 if b in seen:return set()
 seen.add(b);result=set()
 for pin,bufcell in sinks.get(b,()):
  if bufcell in buf_outputs:result.update(terminal_sinks(buf_outputs[bufcell],seen.copy()))
  else:result.add(pin)
 return result
flatloads={b:len(terminal_sinks(b)) for b in loads}
controls=[]
for alias,b in sorted(control_aliases.items()):
 root=b;seen=set()
 while root in buf_inputs and root not in seen:seen.add(root);root=buf_inputs[root]
 controls.append({'alias':alias,'direct_loads':loads[b],'root_driver':drivers.get(root,'top_input'),'root_direct_loads':loads[root],'root_through_buffers_loads':flatloads.get(root,0)})
rank=sorted(loads,key=lambda b:loads[b],reverse=True)
rows=[{'net':names.get(b,str(b)),'driver':drivers.get(b,'top_input'),'loads':loads[b]} for b in rank]
json.dump({'kind':'ASAP7_TT_recursive_primitive_pin_census','top':top,'primitive_cells':leaves,'primitive_types':dict(celltypes),'unmapped_internal_cells':{k:v for k,v in celltypes.items() if k.startswith('$')},'asr_model_proof':'NONE: counts only, never behavioral equivalence','controls':controls,'max_through_buffers_loads':max(flatloads.values(),default=0),'clock_exclusion':'ck_w and ck_r only','maximum_loads':max(loads.values(),default=0),'violations':[r for r in rows if r['loads']>32],'top_drivers':rows[:30],'through_buffer_violations':[{'net':names.get(b,str(b)),'loads':v} for b,v in flatloads.items() if v>32],'pass':not any(r['loads']>32 for r in rows) and max(flatloads.values(),default=0)<=32,'limits':'Physical reach/depth/storage/registered-boundary remain separate; no cell-model equivalence claim'},sys.stdout,indent=2);print()

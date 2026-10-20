#!/usr/bin/env python3
"""MODEL only, exact NOR27 retimed-status cone from safe_pr32.
No RTL emitted. Balanced AND of the existing landed QN states implements its
same-edge Boolean function, including four-state inversion semantics.
"""
import collections,hashlib,json,re,sys
src=open(sys.argv[1]).read();out=sys.argv[2]
cre=re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$',re.M)
outs={'Y','QN','Q','H','L','CON','SN'}
cells={n:(m,dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',p))) for m,n,p in cre.findall(src)}
drivers={v:(n,p) for n,(m,ps) in cells.items() for p,v in ps.items() if p in outs}
loads=collections.defaultdict(list)
for n,(m,ps) in cells.items():
 for p,v in ps.items():
  if p not in outs:loads[v].append((n,p))
root='n6774';fn,fp=drivers[root];fm,fps=cells[fn]
assert fm=='INVx1_ASAP7_75t_R'
remove={fn};leafs={};logic=set()
def walk(net):
 n,p=drivers[net];m,ps=cells[n]
 if m.startswith('OR'):
  assert p=='Y';logic.add(n);remove.add(n)
  return 1+max(walk(v) for k,v in ps.items() if k!='Y')
 assert m=='INVx1_ASAP7_75t_R' and p=='Y'
 q=ps['A'];ff,qpin=drivers[q];ffm,ffps=cells[ff]
 assert ffm=='DFFHQNx1_ASAP7_75t_R' and qpin=='QN'
 assert ffps['CLK']=='n4'
 leafs[q]=dict(ff=ff,master=ffm,pins=ffps,input_inverse=n)
 return 0
depth=walk(fps['A'])
assert len(leafs)==27 and len(logic)==8 and len(remove)==9
for n in remove-{fn}:
 for net in [v for p,v in cells[n][1].items() if p in outs]:
  assert all(c in remove for c,p in loads[net]),(n,net)
masters=collections.Counter(cells[n][0] for n in remove)
nodes=[];current=sorted(leafs);level=0
while len(current)>1:
 following=[];level+=1
 for i in range(0,len(current),4):
  chunk=current[i:i+4]
  if len(chunk)==1:following+=chunk;continue
  m={2:'AND2x2_ASAP7_75t_R',3:'AND3x1_ASAP7_75t_R',4:'AND4x1_ASAP7_75t_R'}[len(chunk)]
  node=dict(name=f'cpr27_{level}_{i//4}',master=m,inputs=chunk,output=f'npr27_{level}_{i//4}',level=level)
  nodes.append(node);following.append(node['output'])
 current=following
nodes[-1]['output']=root
model=dict(schema='opentallas.attn_balanced27_model.v1',source_sha256=hashlib.sha256(src.encode()).hexdigest(),root=root,truth='old INV(OR27(INV(landed_QN))) == AND27(landed_QN)',old_or_levels=depth,old_gate_levels_from_qn=depth+2,new_gate_levels_from_qn=level,serial_edge_delta=0,added_ff=0,removed_cells=sorted(remove),removed_masters=dict(masters),added_masters=dict(collections.Counter(n['master'] for n in nodes)),leaves=leafs,nodes=nodes,clock='same existing n4; no clock/constraint changes',first_last_registers='same existing landing FFs and output-launch FFs')
json.dump(model,open(out,'w'),indent=2)
print(json.dumps({k:v for k,v in model.items() if k not in ('leaves','nodes')}))

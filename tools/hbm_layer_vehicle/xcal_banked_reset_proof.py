#!/usr/bin/env python3
"""Prove source-bound balanced two-edge reset topology in a mapped banked leaf.
Analysis only: no gate waiver, no STA or physical acceptance.
"""
import argparse,collections,hashlib,json,pathlib,re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('mapped');p.add_argument('census');p.add_argument('--output',required=True);a=p.parse_args()
rawdata=pathlib.Path(a.mapped).read_bytes();design=json.loads(rawdata);census=json.loads(pathlib.Path(a.census).read_text());top=census['top'];m=design['modules'][top];cells=m['cells'];raw=m['ports']['rst_n']['bits'][0];clk=m['ports']['clk']['bits'][0]
loads=collections.defaultdict(list);drivers={}
for name,c in cells.items():
 for port,bits in c['connections'].items():
  for b in bits:
   if c['port_directions'][port]=='output':drivers[b]=(name,port)
   else:loads[b].append((name,port))
def transparent(c):return bool(re.match(r'^(INV|BUF)',c['type']))
def leaves(bit,seen=frozenset()):
 assert bit not in seen,'buffer cycle'
 result=set()
 for name,port in loads[bit]:
  c=cells[name]
  if transparent(c):
   for op,bs in c['connections'].items():
    if c['port_directions'][op]=='output':
     for b in bs:result.update(leaves(b,seen|{bit}))
  else:result.add((name,port))
 return result
def origin(bit,parity=0):
 if bit not in drivers:return None,bit,parity
 name,port=drivers[bit];c=cells[name]
 if transparent(c):
  ins=[b for pt,bs in c['connections'].items() if c['port_directions'][pt]=='input' for b in bs]
  assert len(ins)==1
  return origin(ins[0],parity^int(c['type'].startswith('INV')))
 return name,port,parity
roots=leaves(raw);assert len(roots)<=12,(len(roots),'raw profile exceeds12')
rootnames={n for n,p in roots}
assert all(port=='RESETN' and cells[n]['type'].startswith('DFFASRHQN') for n,port in roots),'raw reaches non-root async cells'
phase=[n for n in rootnames if cells[n]['connections']['D']==['1']];assert len(phase)==1,'exactly one first stage required';phase=phase[0]
assert cells[phase]['connections']['CLK']==[clk]
assert cells[phase]['connections']['SETN']==['1']
phaseqn=cells[phase]['connections']['QN'][0];firstloads=leaves(phaseqn);assert len(firstloads)<=24
assert firstloads=={(n,'D')for n in rootnames if n!=phase},'first stage must drive only all second-stage D pins'
final=[]
for name in sorted(rootnames-{phase}):
 c=cells[name];assert c['connections']['CLK']==[clk] and c['connections']['SETN']==['1']
 assert origin(c['connections']['D'][0])==(phase,'QN',1),'second stage D must equal noninverted first-stage logical Q'
 qn=c['connections']['QN'][0];sinks=leaves(qn);assert len(sinks)<=30,(name,len(sinks))
 for sink,port in sinks:
  assert port=='RESETN' and cells[sink]['type'].startswith('DFFASRHQN'),(name,sink,port)
  assert origin(cells[sink]['connections'][port][0])==(name,'QN',1),'functional reset must be logical stage2 Q'
 final.append({'root':name,'buffer_collapsed_reset_loads':len(sinks),'sinks':[list(x)for x in sorted(sinks)]})
# Bind proof to exact source snapshot as well as mapped cell graph.
for path,digest in census['source_sha256'].items():
 assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest,('stale source',path)
report={'top':top,'status':'SOURCE_MAPPED_TWOLEVEL_PASS_NOT_PHYSICAL_APPROVAL','limits':{'raw':12,'first':24,'final':30},'raw_loads':len(roots),'first_stage_D_loads':len(firstloads),'final_max_loads':max(x['buffer_collapsed_reset_loads']for x in final),'root_clock_port':'clk','phase0_root':phase,'final_roots':final,'equations':['q0[t+1]=1 when rst_n=1; q0 asynchronously clears to0','q1_i[t+1]=q0[t]; every q1_i asynchronously clears to0','logical q1_i releases after exactly second root-clock rising edge; all functional RESETN loads equal q1_i through INV/BUF only'],'release_edges':2,'mapped_sha256':hashlib.sha256(rawdata).hexdigest(),'source_sha256':census['source_sha256']}
pathlib.Path(a.output).write_text(json.dumps(report,indent=2)+'\n');print(top,report['raw_loads'],report['first_stage_D_loads'],report['final_max_loads'],'PASS')

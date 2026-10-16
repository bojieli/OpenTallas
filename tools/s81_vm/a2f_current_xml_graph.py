#!/usr/bin/env python3
"""Source-current XML hard-boundary graph. Pure wires are joined bit-exactly.
Operators/procedural logic are explicit physical-home gaps, never discarded or
silently treated as wires. Dynamic lvalues produce conservative dependency nodes
and block exact-cut qualification. This is a source graph audit, not synthesis.
"""
import argparse,collections,gzip,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--xml',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 root=ET.parse(a.xml).getroot();net=root.find('netlist');mods={m.get('name'):m for m in net.findall('module')};types={t.get('id'):t for t in net.find('typetable')}
 inv=json.loads((ROOT/'results/arch/s81_vm_area_1417/a2_inventory.json').read_text())
 hard={l['master'] for l in inv['leaves']}|{'s81_a2f_field4','s81_a2f_control4_resetlocal','s81_a2f_fault_join4','dsfd_vm_a2f_rsched_p','dsfd_vm_static_wfc_ctl'}
 # Inventory's A2 substitution names differ from actual source; expand wrappers and stop on implemented leaves.
 hard.discard('s81_a2_stripe_data16');hard.discard('s81_a2_stripe_meta26')
 unknown=collections.Counter();scope_env={};uf={};rank={};leaves=[];pending=[];logic=[];alias_blocks=[];exprseq=0
 def find(x):
  trail=[]
  while x in uf:trail.append(x);x=uf[x]
  for t in trail:uf[t]=x
  return x
 def union(x,y):
  x,y=find(x),find(y)
  if x==y:return
  if rank.get(x,0)<rank.get(y,0):x,y=y,x
  uf[y]=x
  if rank.get(x,0)==rank.get(y,0):rank[x]=rank.get(x,0)+1
 def const(n):
  s=n.get('name');b=re.fullmatch(r"(\d+)'(s?)([hbod])([0-9a-fA-FxXzZ_]+)",s or '')
  if not b:raise ValueError(s)
  if re.search('[xXzZ]',b[4]):raise ValueError('four-state '+s)
  return int(b[4].replace('_',''),{'h':16,'b':2,'o':8,'d':10}[b[3]])
 def dtwidth(t):
  d=types[t]
  if d.tag in ('basicdtype','enumdtype'):return abs(int(d.get('left',0))-int(d.get('right',0)))+1 if d.tag=='basicdtype' else dtwidth(d.get('sub_dtype_id'))
  if d.tag in ('packarraydtype','unpackarraydtype'):
   rr=d.find('range');x,y=[const(x) for x in rr];return (abs(x-y)+1)*dtwidth(d.get('sub_dtype_id'))
  if d.get('sub_dtype_id'):return dtwidth(d.get('sub_dtype_id'))
  unknown['DTYPE:'+d.tag]+=1;return 1
 def width(n):return dtwidth(n.get('dtype_id')) if n.get('dtype_id') else 1
 def refs(n,path):
  out={}
  for v in n.iter('varref'):
   k=v.get('name');scope=scope_env.get((path,id(v)),{}).get(k,path);out[(scope,k)]=width(v)
  return [(scope,k,b) for (scope,k),w in out.items() for b in range(w)]
 def prepare_scope(m,path):
  def rec(n,env,scope):
   if n is not m and n.tag=='begin' and n.get('name'):scope+='.'+n.get('name')
   vv=n.findall('var')
   if vv:
    env=dict(env)
    for v in vv:env[v.get('name')]=scope
   scope_env[(path,id(n))]=env
   for c in n:rec(c,env,scope)
  rec(m,{},path)
 def expr(n,path):
  nonlocal exprseq
  t=n.tag;cs=list(n)
  if t=='varref':return [(scope_env.get((path,id(n)),{}).get(n.get('name'),path),n.get('name'),b) for b in range(width(n))]
  if t=='const':
   try:v=const(n);return [('CONST',str((v>>b)&1),0) for b in range(width(n))]
   except ValueError:unknown['CONST_UNKNOWN']+=1
  if t=='sel' and len(cs)==3 and cs[1].tag==cs[2].tag=='const':
   lo=const(cs[1]);w=const(cs[2]);return expr(cs[0],path)[lo:lo+w]
  if t=='concat':return sum((expr(c,path) for c in reversed(cs)),[])
  if t=='replicate' and len(cs)==2 and cs[1].tag=='const':return expr(cs[0],path)*const(cs[1])
  if t in ('extend','extends'):
   x=expr(cs[0],path);return (x+[x[-1] if t=='extends' else ('CONST','0',0)]*width(n))[:width(n)]
  exprseq+=1;label=f'{path}.$expr{exprseq}:{t}';outs=[(label,'out',b) for b in range(width(n))]
  rs=refs(n,path);logic.append(dict(path=label,kind='expression',operation=t,source_loc=n.get('loc'),input_bits=len(rs),output_bits=len(outs),physical_home=None,exact_mapping=False))
  idx=-(len(logic)+1)
  for b,v in enumerate(rs):pending.append((v,(idx,'in',b,'INPUT')))
  for b,v in enumerate(outs):pending.append((v,(idx,'out',b,'OUTPUT')))
  unknown['EXPRESSION:'+t]+=1
  return outs
 def join(x,y,where):
  if len(x)!=len(y):unknown['WIDTH_MISMATCH:'+where]+=1;return
  for xx,yy in zip(x,y):union(xx,yy)
 def local(m):
  for c in m:
   yield c
   if c.tag in ('begin','genblk'):yield from local(c)
 def instances(m,prefix=''):
  for c in m:
   if c.tag=='instance':yield prefix+c.get('name'),c
   elif c.tag in ('begin','genblk'):
    nm=c.get('name','');yield from instances(c,prefix+(nm+'.' if nm else ''))
 def static_alias(block,path):
  env={};state={}
  def key(n):return (scope_env.get((path,id(n)),{}).get(n.get('name'),path),n.get('name'))
  def integer(n):return n.tag=='varref' and types[n.get('dtype_id')].get('name')=='integer'
  def number(n):
   t=n.tag;cs=list(n)
   if t=='const':
    v=const(n);w=width(n)
    return v-(1<<w) if "'s" in n.get('name') and v&(1<<(w-1)) else v
   if t=='varref' and key(n) in env:return env[key(n)]
   if t=='sel':return (number(cs[0])>>number(cs[1]))&((1<<number(cs[2]))-1)
   if t=='cond':return number(cs[1] if number(cs[0]) else cs[2])
   if t in ('extend','extends'):return number(cs[0])
   if t in ('add','sub','mul','muls','gts','lts','gt','lt','gte','lte','eq','neq','and','or','xor'):
    x,y=number(cs[0]),number(cs[1]);return {'add':lambda:x+y,'sub':lambda:x-y,'mul':lambda:x*y,'muls':lambda:x*y,'gts':lambda:int(x>y),'lts':lambda:int(x<y),'gt':lambda:int(x>y),'lt':lambda:int(x<y),'gte':lambda:int(x>=y),'lte':lambda:int(x<=y),'eq':lambda:int(x==y),'neq':lambda:int(x!=y),'and':lambda:x&y,'or':lambda:x|y,'xor':lambda:x^y}[t]()
   raise ValueError('runtime control/value '+t)
  def value(n,dest=False):
   t=n.tag;cs=list(n)
   if t=='varref' and not integer(n):
    pp,kk=key(n);vs=[(pp,kk,b) for b in range(width(n))]
    return vs if dest else [state.get(v,v) for v in vs]
   if t=='sel':
    lo=number(cs[1]);w=number(cs[2]);return value(cs[0],dest)[lo:lo+w]
   if t=='concat':return sum((value(c,dest) for c in reversed(cs)),[])
   if t=='replicate':return value(cs[0],dest)*number(cs[1])
   if t in ('extend','extends'):
    x=value(cs[0],dest);return (x+[x[-1] if t=='extends' else ('CONST','0',0)]*width(n))[:width(n)]
   v=number(n);return [('CONST',str((v>>b)&1),0) for b in range(width(n))]
  def run(n):
   t=n.tag;cs=list(n)
   if t in ('begin','always'):
    for c in cs:run(c)
   elif t=='assign':
    rhs,lhs=cs
    if integer(lhs):env[key(lhs)]=number(rhs)
    else:
     x,y=value(lhs,True),value(rhs)
     if len(x)!=len(y):raise ValueError('static alias width mismatch')
     state.update(zip(x,y))
   elif t=='while':
    init,cond,body,inc=cs;run(init)
    for iteration in range(4096):
     if not number(list(cond)[0]):break
     run(body);run(inc)
    else:raise ValueError('unbounded static alias loop')
   elif t=='if':
    run(cs[1] if number(cs[0]) else cs[2])
   elif t not in ('var','comment'):raise ValueError('unsupported alias statement '+t)
  run(block);return state
 def procedural_dependencies(block,path):
  dep=collections.defaultdict(set)
  def vv(n):return {(p,k) for p,k,b in refs(n,path)}
  def destinations(n):
   if n.tag=='varref':return vv(n)
   if n.tag in ('sel','arraysel'):return destinations(list(n)[0])
   if n.tag=='concat':return set().union(*(destinations(c) for c in n))
   return set()
  def visit(n,controls):
   cs=list(n)
   if n.tag in ('assign','assigndly') and len(cs)==2:
    rhs,lhs=cs;src=vv(rhs)|controls
    if lhs.tag in ('sel','arraysel'):
     for c in list(lhs)[1:]:src|=vv(c)
    for d in destinations(lhs):dep[d]|=src
   elif n.tag=='if':
    ctrl=controls|vv(cs[0])
    for c in cs[1:]:visit(c,ctrl)
   elif n.tag=='while' and len(cs)==4:
    visit(cs[0],controls);ctrl=controls|vv(cs[1]);visit(cs[2],ctrl);visit(cs[3],ctrl)
   else:
    for c in cs:visit(c,controls)
  visit(block,set())
  return {p+'.'+k:sorted(q+'.'+v for q,v in ds) for (p,k),ds in dep.items()}
 def recurse(m,path,connections=None):
  prepare_scope(m,path)
  vs=[v for v in m.findall('var') if v.get('dir')in ('input','output','inout')]
  if connections is not None:
   for v in vs:
    if v.get('name') in connections:join([(path,v.get('name'),b) for b in range(width(v))],connections[v.get('name')],path+'.'+v.get('name'))
  name=m.get('origName')
  if name in hard:
   params={v.get('name'):const(list(v)[0]) for v in m.findall('var') if v.get('param')=='true' and len(v) and list(v)[0].tag=='const'}
   i=len(leaves);leaves.append(dict(path=path,master=name,elaborated_module=m.get('name'),parameters=params,ports={v.get('name'):dict(direction=v.get('dir'),bits=width(v)) for v in vs},physical_home=None))
   for v in vs:
    for b in range(width(v)):pending.append(((path,v.get('name'),b),(i,v.get('name'),b,v.get('dir').upper())))
   return
  for n in local(m):
   if n.tag=='contassign':
    rhs,lhs=list(n);join(expr(lhs,path),expr(rhs,path),path+':contassign')
   elif n.tag in ('always','initial','final'):
    if n.tag=='always' and n.find('sentree') is None:
     try:aliases=static_alias(n,path)
     except (ValueError,KeyError,IndexError):aliases=None
     if aliases is not None:
      for x,y in aliases.items():union(x,y)
      alias_blocks.append(dict(path=path,source_loc=n.get('loc'),assigned_bits=len(aliases)))
      continue
    writes={};reads={}
    for assign in n.iter():
     if assign.tag in ('assign','assigndly') and len(assign)==2:
      rhs,lhs=list(assign)
      for p,k,b in refs(lhs,path):writes.setdefault((p,k),set()).add(b)
    for p,k,b in refs(n,path):reads.setdefault((p,k),set()).add(b)
    label=f'{path}.${n.tag}{len(logic)}';li=len(logic);logic.append(dict(path=label,kind=n.tag,source_loc=n.get('loc'),physical_home=None,exact_mapping=False,write_vars={p+'.'+k:len(v) for (p,k),v in writes.items()},read_vars={p+'.'+k:len(v) for (p,k),v in reads.items()},output_dependencies=procedural_dependencies(n,path),note='Conservative variable-level dependencies; exact dynamic bit mapping pending. Not a hard tile.'))
    idx=-(li+2)
    for (p,k),bs in reads.items():
     for b in bs:pending.append(((p,k,b),(idx,'read:'+k,b,'INPUT')))
    for (p,k),bs in writes.items():
     for b in bs:pending.append(((p,k,b),(idx,'write:'+k,b,'OUTPUT')))
  for name,c in instances(m):
   child=mods[c.get('defName')];position={v.get('pinIndex'):v.get('name') for v in child.findall('var') if v.get('dir')}
   bindings={position[p.get('portIndex')] if p.get('name','').startswith('__pinNumber') else p.get('name'):expr(list(p)[0],path) for p in c.findall('port') if len(p)}
   recurse(child,path+'.'+name,bindings)
 top=next(m for m in mods.values() if m.get('topModule')=='1');recurse(top,'dut')
 for v in top.findall('var'):
  if v.get('dir') in ('input','output'):
   for b in range(width(v)):pending.append((('dut',v.get('name'),b),(-1,v.get('name'),b,'OUTPUT' if v.get('dir')=='input' else 'INPUT')))
 groups=collections.defaultdict(list)
 for v,e in pending:groups[find(v)].append(e)
 constant_roots={find(('CONST','0',0)),find(('CONST','1',0))};assert len(constant_roots)==2,'constant0/1 alias conflict'
 counts=collections.Counter();gaps=collections.Counter();a.out.mkdir(parents=True,exist_ok=True)
 with gzip.open(a.out/'pin_join.jsonl.gz','wt') as f:
  for key,es in groups.items():
   ds=[e for e in es if e[3]=='OUTPUT'];cs=[e for e in es if e[3]=='INPUT'];st='CONSTANT' if key in constant_roots else 'ONE_DRIVER' if len(ds)==1 else 'MULTIPLE_DRIVERS' if ds else 'UNDRIVEN'
   counts[st]+=1
   for i,p,b,d in cs:
    if i>=0 and (st!='ONE_DRIVER' or any(e[0]<-1 for e in ds)):gaps[(leaves[i]['master'],p,st)]+=1
   f.write(json.dumps(dict(status=st,drivers=ds,consumers=cs),separators=(',',':'))+'\n')
 # Traverse variable-level operator dependencies from actual hard inputs / top outputs.
 # Procedural outputs are independent roots; a dead d bus does not make data feed a live valid/fault output.
 reverse=collections.defaultdict(set);live=set();toproles=collections.Counter()
 def outkey(e):return (e[0],e[1])
 for es in groups.values():
  ds=[e for e in es if e[3]=='OUTPUT'];cs=[e for e in es if e[3]=='INPUT']
  for d in ds:
   for c in cs:
    if d[0]==-1 and c[0]>=0:toproles[(d[1],'input',leaves[c[0]]['path'],c[1])]+=1
    if c[0]==-1 and d[0]>=0:toproles[(c[1],'output',leaves[d[0]]['path'],d[1])]+=1
  src={outkey(d) for d in ds if d[0]<-1}
  if any(c[0]>=-1 for c in cs):live|=src
  for c in cs:
   if c[0]>=-1:continue
   node=logic[-c[0]-2]
   if node['kind']=='expression':affected=['out']
   else:
    nm=c[1].removeprefix('read:')
    readnames={k for k in node.get('read_vars',{}) if k.endswith('.'+nm)}
    affected=['write:'+k.rsplit('.',1)[-1] for k,vs in node.get('output_dependencies',{}).items() if readnames.intersection(vs)]
   for op in affected:reverse[(c[0],op)]|=src
 queue=list(live)
 while queue:
  v=queue.pop()
  for u in reverse[v]:
   if u not in live:live.add(u);queue.append(u)
 obs=[]
 for j,node in enumerate(logic):
  idx=-(j+2);written=['out'] if node['kind']=='expression' else ['write:'+k.rsplit('.',1)[-1] for k in node.get('write_vars',{})]
  obs.append(dict(path=node['path'],kind=node['kind'],observable_outputs=sorted(op for op in set(written) if (idx,op) in live),unobserved_outputs=sorted(op for op in set(written) if (idx,op) not in live),scope='Variable-level conservative dependency BFS; roots actual hard-boundary inputs and parent outputs'))
 (a.out/'observability.json').write_text(json.dumps(obs,indent=1)+'\n')
 (a.out/'role_anchors.json').write_text(json.dumps([dict(role=p,direction=d,leaf_path=l,leaf_port=pp,bits=n) for (p,d,l,pp),n in sorted(toproles.items())],indent=1)+'\n')
 # Full hierarchy SRAM count is independent of chosen hard boundaries.
 def census(m):
  out=collections.Counter({m.get('origName'):1})
  for _,c in instances(m):out.update(census(mods[c.get('defName')]))
  return out
 cc=census(top)
 summary=dict(schema='opentallas.s81.vm-source-current-xml-graph.v1',status='SOURCE_CURRENT_GRAPH_WITH_EXPLICIT_PHYSICAL_GAPS_NOT_CUT_QUALIFIED',xml_path=str(a.xml),xml_sha256=hashlib.sha256(a.xml.read_bytes()).hexdigest(),hard_leaves=len(leaves),hierarchical_sram_macros=cc['ot_sram_1r1w_512x128_m4_r2c2'],hard_families=dict(collections.Counter(l['master'] for l in leaves)),join_status=dict(counts),unknown_operations=dict(unknown),softlogic_nodes=len(logic),static_alias_blocks=alias_blocks,physical_home_gaps=[dict(master=m,port=p,status=s,bits=n) for (m,p,s),n in gaps.most_common()],scope='All chosen hard-boundary ports enumerated; pure wires bit-exact; operators/procedural nodes explicit with no physical home. Conservative procedural/dynamic dependencies do NOT establish exact connectivity/cut.',not_claimed=['Exact procedural dynamic bit mapping','Physical placement or clock delivery','Native closure or throughput','Any <0.60 complete cut'])
 for name,data in [('inventory.json',dict(leaves=leaves)),('parent_logic.json',logic),('summary.json',summary)]: (a.out/name).write_text(json.dumps(data,indent=1)+'\n')
 print(json.dumps(summary,indent=1))
if __name__=='__main__':main()

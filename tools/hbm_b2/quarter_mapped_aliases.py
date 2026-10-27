#!/usr/bin/env python3
"""Exact connectivity aliases for source-logical FF banks in a hierarchical mapped JSON.
Diagnostic only: bare synthesis can merge source FFs; never silently duplicate cells.
"""
import argparse,json,re,collections,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--netlist',type=Path,required=True);ap.add_argument('--graph',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
M=json.load(open(a.netlist))['modules'];top='ot_hnx_idxn_quarter_with_keybuf';G=json.load(open(a.graph));cache={};chains={}
def cellgraph(mod):
 if mod in cache:return cache[mod]
 m=M[mod];drive={}
 for n,c in m.get('cells',{}).items():
  for p,dr in c.get('port_directions',{}).items():
   if dr=='output':
    for b in c['connections'].get(p,[]):
     if isinstance(b,int):drive[b]=(n,c,p)
 cache[mod]=(m,drive);return m,drive

def seqset(mod,b,seen=None):
 # Stop at the first actual sequential cells, allowing only exact netlist edges.
 if not isinstance(b,int):return set()
 seen=set()if seen is None else seen
 if b in seen:return set()
 seen.add(b);m,drv=cellgraph(mod)
 if b not in drv:return set()
 n,c,p=drv[b]
 if c['type'].startswith('DFF'):return{n}
 if c['type']in M and M[c['type']].get('cells'):return set()
 out=set()
 for pin,dr in c.get('port_directions',{}).items():
  if dr=='input':
   for bit in c['connections'].get(pin,[]):out.update(seqset(mod,bit,seen))
 return out

def locate(path):
 mod=top;prefix='';rest=path
 while True:
  m=M[mod];hits=[n for n,c in m.get('cells',{}).items()if c['type']in M and rest.startswith(n+'.')]
  if not hits:return mod,prefix,rest
  n=max(hits,key=len);mod=m['cells'][n]['type'];prefix+=n+'.';rest=rest[len(n)+1:]

def netbit(mod,nm):
 ns=M[mod].get('netnames',{})
 if nm in ns and len(ns[nm]['bits'])==1:return ns[nm]['bits'][0]
 q=re.fullmatch(r'(.*)\[(\d+)\]',nm)
 if q and q[1]in ns:
  nn=ns[q[1]];idx=int(q[2])-nn.get('offset',0)
  if 0<=idx<len(nn['bits']):return nn['bits'][idx]
 raise KeyError(nm)

def delaychain(mod,b,depth):
 key=(mod,b,depth)
 if key in chains:return chains[key]
 bit=netbit(mod,f'q[{b}]');cells=[];seen=set();m=M[mod]
 for st in range(depth):
  ff=seqset(mod,bit)
  if len(ff)!=1:raise ValueError(f'delay stage{st} has{len(ff)} sequential predecessors')
  n=next(iter(ff))
  if n in seen:raise ValueError('repeated FF in delay chain')
  seen.add(n);cells.append(n);cc=m['cells'][n]
  if len(cc['connections'].get('D',[]))!=1:raise ValueError('non-scalar delay D')
  bit=cc['connections']['D'][0]
 # Exact expected depth must end at the same module input data bit (possibly invert/buffer).
 if seqset(mod,bit):raise ValueError('delay longer than declared depth')
 cells.reverse();chains[key]=cells;return cells

records={};counts=collections.Counter();bycell=collections.defaultdict(list)
for name,coord in G['anchors'].items():
 path='scorer.'+name
 special=re.match(r'(.*\.(?:keep_pipe|md))\.line\[(\d+)\]\[(\d+)\]$',name)
 uv=re.match(r'(.*\.u_vl)\.logical_stage\[(\d+)\]\[(\d+)\]$',name)
 try:
  if special or uv:
   q=special or uv;base,st,b=q[1],int(q[2]),int(q[3]);dep=123 if '.md' in base else 106 if '.keep_pipe'in base else 104
   target='scorer.'+base+('.delay'if '.md'in base else'')+'.q'
   mod,prefix,rest=locate(target);cell=delaychain(mod,b,dep)[st];kind='EXACT_PIPELINE_CHAIN'
  else:
   mod,prefix,rest=locate(path);bit=netbit(mod,rest)
   if isinstance(bit,str):records[name]=dict(kind='CONSTANT_OR_X',value=bit,point_um=coord);counts['CONSTANT_OR_X']+=1;continue
   ff=seqset(mod,bit)
   if len(ff)!=1:raise ValueError(f'{len(ff)} sequential drivers')
   cell=next(iter(ff));kind='EXACT_SEQUENTIAL_DRIVER'
  full=prefix+cell;typ=M[mod]['cells'][cell]['type'];records[name]=dict(kind=kind,cell=full,cell_type=typ,point_um=coord);bycell[full].append(name);counts[kind]+=1
 except(KeyError,ValueError,IndexError)as ex:
  records[name]=dict(kind='UNRESOLVED',reason=str(ex),point_um=coord);counts['UNRESOLVED']+=1
conflicts=[]
for cell,names in bycell.items():
 positions={tuple(G['anchors'][n])for n in names}
 if len(positions)>1:conflicts.append(dict(cell=cell,logical_identities=names,proposed_coordinates=sorted(positions)))
sumry=dict(schema='opentallas.native_quarter_bare_mapped_aliases.v1',source='ef994fe770 /44a5cccc2d',mapped_json_sha256=hashlib.sha256(a.netlist.read_bytes()).hexdigest(),counts=counts,unique_mapped_cells=len(bycell),merged_cells_multiple_points=conflicts,qualification='DIAGNOSTIC_BARE_SYNTHESIS_NO_PRODUCTION_KEEP_HOOK; no placement or equivalence acceptance')
json.dump(sumry,open(a.out/'summary.json','w'),indent=2);json.dump(records,open(a.out/'aliases.json','w'),indent=2);print(json.dumps(dict(counts=counts,unique_cells=len(bycell),coordinate_conflicts=len(conflicts))))

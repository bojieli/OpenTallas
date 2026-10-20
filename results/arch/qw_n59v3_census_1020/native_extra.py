import sys,json,re,collections,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import textbook_lint as T
net=Path(sys.argv[2]);top=sys.argv[3];out=Path(sys.argv[4])
g,top=T.flatten(T.parse_verilog(net.read_text()),top);a=T.build(g,None);kind=a['kind'];drivers=a['driver'];loads=a['loads'];clocks=set()
for ci,(typ,name,pins) in enumerate(g.cells):
 if kind[ci]=='ff':
  for p in T.SEQ_CLK_PINS:clocks.update(pins.get(p,[]))
hf=[]
for x,d in drivers.items():
 if x in clocks or x<=3 or (d[0]>=0 and kind[d[0]] in ['buf','tie']):continue
 count,ff,ex=T.bufinv_fanout(g,a,x,clocks)
 if count>32:hf.append(dict(net=T.net_label(g,a,x),loads=count,flops=ff,example=ex))
hf.sort(key=lambda v:-v['loads'])
for rec in hf[:8]:
 seed=next(x for x in drivers if T.net_label(g,a,x)==rec['net'])
 queue=collections.deque([(seed,0)]);seen=set();origins=[]
 while queue and len(origins)<24:
  x,depth=queue.popleft()
  if x in seen or depth>12:continue
  seen.add(x);d=drivers.get(x)
  if not d:continue
  ci,pin=d
  if ci<0:origins.append('PORT '+pin);continue
  typ,name,pins=g.cells[ci]
  if kind[ci] in ['ff','macro']:origins.append(typ+' '+name+'/'+pin);continue
  for pn,bs in pins.items():
   if a['pin_dir'][ci].get(pn)=='in':queue.extend((b,depth+1) for b in bs)
 rec['upstream_source_examples']=origins

tied=[]
for name,(direction,x) in g.ports.items():
 if direction=='output' and (x<=3 or (x in drivers and drivers[x][0]>=0 and kind[drivers[x][0]]=='tie')):tied.append(name)
regs=collections.Counter()
for ci,(typ,name,pins) in enumerate(g.cells):
 if kind[ci]=='ff':
  prefix,sep,leaf=name.rpartition('.')
  leaf=re.sub(r'\[\d+\].*$', '',leaf)
  leaf=re.sub(r'\$.*$', '',leaf)
  base=prefix+sep+leaf
  regs[base]+=1
large=[dict(family=k,bits=v) for k,v in regs.items() if v>2048]
result=dict(schema='codex.n59.native_mapped_census.v1',netlist_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),top=top,flops=kind.count('ff'),macros=kind.count('macro'),drivers_over32=hf,tied_output_bits=tied,flop_families_over2048=large,limitations=['No physical reach from synthesis-only netlist','Tied output bits require functional field classification; no blanket waiver','Storage family grouping is diagnostic; RTL inventory also required','Pins: use strict textbook boundary levels and inspect actual cones; no full independent pin-clearance claim'])
out.write_text(json.dumps(result,indent=2)+'\n')
print(top,'over32',len(hf),'max',hf[:2],'tied output bits',len(tied),'large families',large)

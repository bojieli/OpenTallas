"""Export measured standard-flop bins for only the local core-clock roots.
Forwarded-clock roots stay separate; unknown clocks fail instead of entering the core census.
"""
import sys,json,re,hashlib,collections
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])))
import geom_rules as G
src,out=Path(sys.argv[2]),Path(sys.argv[3]);D=G.Design(src)
P={p['k']:p for p in D.pins};memo={}
def root(n,seen=()):
 if n in memo:return memo[n]
 if n in seen:raise ValueError('clock loop')
 if n in D.multi_drv and len(D.multi_drv[n])>1:raise ValueError('parallel clock drivers')
 dr=D.nets[n][1]
 if not dr:raise ValueError('undriven clock net')
 if dr[0]=='p':v=P[dr[1]]['name']
 else:
  if D.kind(dr[1]) not in ('B','K'):raise ValueError('nonbuffer clock driver '+D.cells[dr[1]][6])
  ins=D.cell_in.get(dr[1],[]);ns=[nn for nn,ck in ins if ck]
  if not ns:ns=[nn for nn,ck in ins]
  if len(ns)!=1:raise ValueError('ambiguous clock buffer inputs')
  v=root(ns[0],seen+(n,))
 memo[n]=v;return v
bins=collections.Counter();roots=collections.Counter();excluded=collections.Counter();bad=[];BIN=10.8
for cid,c in D.cells.items():
 if c[0]!='S':continue
 try:
  ns=[n for n,ck in D.cell_in.get(cid,[]) if ck]
  if not ns:raise ValueError('unclocked sequential cell')
  rr={root(n) for n in ns}
  if len(rr)!=1:raise ValueError('multiple clock roots')
  r=next(iter(rr));roots[r]+=1
  if re.fullmatch(r'(clk|ck)(?:_[tc][0-9]+)?',r):
   x,y=G.ctr(c);bins[(int(x//BIN),int(y//BIN))]+=1
  elif r.startswith('fclk_in_'):excluded[r]+=1
  else:raise ValueError('unclassified clock root '+r)
 except ValueError as e:bad.append({'cell':c[6],'error':str(e)})
assert not bad,bad[:10]
assert sum(roots.values())==sum(c[0]=='S' for c in D.cells.values())
assert sum(bins.values())+sum(excluded.values())==sum(roots.values())
d=dict(bin_um=BIN,n=sum(bins.values()),bins=[[round((i+.5)*BIN,3),round((j+.5)*BIN,3),n] for (i,j),n in sorted(bins.items())],
       source='actual legal DPL standard-flop clock roots (pre-CTS), no inferred model sinks',source_dump=str(src),
       source_dump_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),root_counts=dict(roots),
       excluded_forwarded_root_counts=dict(excluded),excluded_forwarded_sinks=sum(excluded.values()),unclassified=[])
out.write_text(json.dumps(d,indent=1)+'\n');print(json.dumps({k:v for k,v in d.items() if k!='bins'},indent=1))

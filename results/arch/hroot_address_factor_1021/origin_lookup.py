import importlib.util,sys,json,hashlib,collections
from pathlib import Path
p=Path('.');sp=importlib.util.spec_from_file_location('T',p/'textbook_lint.py');T=importlib.util.module_from_spec(sp);sys.modules['T']=T;sp.loader.exec_module(T)
raw=(p/'original_mapped.v').read_bytes();assert hashlib.sha256(raw).hexdigest()=='2b34032b15f16130a8bf6de13358f28e7fe5582078ca4102e073766316d7eff3';assert hashlib.sha256((p/'textbook_lint.py').read_bytes()).hexdigest()=='4adb3e6072ab0e5d93ddaa5205d5139c37971aa87175b1923beea9261dd2619b'
g,top=T.flatten(T.parse_verilog(raw.decode()),None);A=T.build(g,None)
print('GRAPH',top,len(g.cells),'CELL80525',g.cells[80525]);print('PREFIX16130',g.cells[16130])
cache={}
def cone(ci):
 if ci in cache:return cache[ci]
 _,_,pins=g.cells[ci];stack=list(pins.get('D',[]));seen=set();ff=set();ports=set()
 while stack:
  x=stack.pop()
  if x in seen:continue
  seen.add(x);driver=A['driver'].get(x)
  if driver is None:continue
  c,pn=driver
  if c<0:ports.add(pn);continue
  if A['kind'][c]=='ff':ff.add(c);continue
  for k,bs in g.cells[c][2].items():
   if A['pin_dir'][c][k]=='in':stack.extend(bs)
 cache[ci]=(ff,ports);return ff,ports
out={}
for ci in [80525,80526,80524]:
 frontier={ci};levels=[];seen=set()
 for depth in range(4):
  nxt=set();ports=set();cells=[]
  for c in frontier-seen:
   ff,pp=cone(c);nxt|=ff;ports|=pp;cells.append(dict(cell=c,name=g.cells[c][1],master=g.cells[c][0],D=[g.net_name[n] for n in g.cells[c][2].get('D',[])],Q=[g.net_name[n] for n in g.cells[c][2].get('QN',[])],upstreamFF=sorted(ff),primary=sorted(pp)))
  levels.append(dict(depth=depth,primary=sorted(ports),cells=cells));seen|=frontier;frontier=nxt
 out[str(ci)]=levels
 print('ORIGIN',ci,[(v['depth'],len(v['cells']),[x for x in v['primary'] if x.startswith('d_data')]) for v in levels])
Path('origin_lookup.json').write_text(json.dumps(out,indent=1)+'\n')

stack=list(g.cells[16153][2]['Y']);seen=set();leaves=set()
while stack:
 n=stack.pop()
 if n in seen:continue
 seen.add(n);dr=A['driver'].get(n)
 if not dr:continue
 c,pn=dr
 if c<0:continue
 if A['kind'][c]=='ff':leaves.add(c);continue
 for k,bs in g.cells[c][2].items():
  if A['pin_dir'][c][k]=='in':stack.extend(bs)
leafrec=[]
for c in sorted(leaves):
 f0,p0=cone(c);ports=set(p0)
 for u in f0:ports.update(cone(u)[1])
 leafrec.append(dict(cell=c,name=g.cells[c][1],master=g.cells[c][0],payload=sorted(x for x in ports if x.startswith('d_data'))))
print('PREFIX_FULL_LEAVES',len(leaves),leafrec)
Path('prefix_leaves.json').write_text(json.dumps(leafrec,indent=1)+'\n')

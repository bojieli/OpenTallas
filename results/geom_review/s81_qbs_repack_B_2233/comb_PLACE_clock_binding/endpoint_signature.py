from pathlib import Path
import sys,json,hashlib,re
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
norm=lambda s:s.replace('\\','')
def signature(geom,macro):
 D=G.Design(geom);C=json.load(open(macro));mp={};pk={p['k']:p['name']for p in D.pins}
 for name,m in C['macros'].items():
  for p in m['ports']:
   if p['geom_net_index']is not None:mp.setdefault((m['cid'],p['geom_net_index'],p['io']),[]).append('M:'+norm(name)+'.'+norm(p['port']))
 def frontier(cid,fwd):
  out=set();todo=[cid];seen=set()
  while todo:
   q=todo.pop()
   if q in seen:continue
   seen.add(q)
   nis=D.drives.get(q,[])if fwd else[n for n,clk in D.cell_in.get(q,[])if not clk]
   for ni in nis:
    sig,dr,sinks=D.nets[ni]
    if sig in('CLOCK','POWER','GROUND'):continue
    refs=sinks if fwd else([('i',v,False)for v in D.multi_drv[ni]]if ni in D.multi_drv else([dr]if dr else[]))
    for r in refs:
     if r[0]=='p':out.add('P:'+pk[r[1]]);continue
     if r[0]!='i'or r[2]:continue
     k=D.kind(r[1])
     if k=='S':out.add('F:'+norm(D.cells[r[1]][6]))
     elif k=='M':out.update(mp[(r[1],ni,'INPUT'if fwd else'OUTPUT')])
     elif k in('B','L','K'):todo.append(r[1])
  return sorted(out)
 hashes={};edges=0
 for cid,c in D.cells.items():
  if c[0]!='S':continue
  a=frontier(cid,False);b=frontier(cid,True);edges+=len(a)+len(b);hashes[norm(c[6])]=hashlib.sha256(json.dumps([a,b],separators=(',',':')).encode()).hexdigest()
 return dict(FF=len(hashes),frontier_entries=edges,hashes=hashes)
if __name__=='__main__':
 a=signature(sys.argv[1],sys.argv[2]);Path(sys.argv[3]).write_text(json.dumps(a));print('source frontier signatures',a['FF'],a['frontier_entries'])

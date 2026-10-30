import sys,json,collections,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import geom_rules as G
D=G.Design(Path(__file__).parent/'geom.tsv');rows=[]
for cid,c in D.cells.items():
 if c[0] not in 'SM':continue
 for n,isclk in D.cell_in.get(cid,[]):
  if not isclk:continue
  cur=n;seen=set()
  while True:
   assert cur not in seen;seen.add(cur);dr=D.nets[cur][1]
   if dr is None:root='UNROOTED';break
   if dr[0]=='p':root=D.pin_by_k[dr[1]]['name'];break
   assert D.kind(dr[1])in('B','K')
   ins=D.cell_in[dr[1]];cl=[i for i,k in ins if k];cur=cl[0]if cl else ins[0][0]
  rows.append(dict(id=cid,name=c[6],xy=G.ctr(c),root=root,master=c[1]))
Path(__file__).with_name('clock_sinks.json').write_text(json.dumps(rows))
r=[a for a in rows if a['root']=='clk'];print('actual',dict(collections.Counter(a['root']for a in rows)))
print('grid',[(p['name'],p['x'],p['y'])for p in D.pins if G.GRID_TAP_RE.match(p['name'])])
print('rclk groups',collections.Counter(a['name'].split('/')[0] for a in r).most_common(22))

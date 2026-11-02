from pathlib import Path
from collections import deque,Counter
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/head-wave-path-query-1102/hd_st_n3_turn/geom5/geom.tsv');byname={c[6].replace(chr(92),''):i for i,c in D.cells.items()};names=['input17','u_cland_u1_i/load_slew5641','u_cland_u1_i/_09236_','u_cland_u1_i/_09276_','u_cland_u1_i/load_slew2126','u_cland_u1_i/load_slew2123','u_cland_u1_i/wire2122','u_cland_u1_i/load_slew2121','u_cland_u1_i/_11569_'];rows=[]
for name in names:
 i=byname[name];c=D.cells[i];outs=[];ins=[]
 for ni,ck in D.cell_in.get(i,[]):
  dr=D.nets[ni][1];ins.append(dict(net_id=ni,clock=ck,driver=None if not dr else ('PORT:'+D.pin_by_k[dr[1]]['name']if dr[0]=='p'else D.cells[dr[1]][6])))
 for ni in D.drives.get(i,[]):
  sig,dr,ss=D.nets[ni];sinks=[dict(id=s[1],name=D.cells[s[1]][6],kind=D.kind(s[1]),clock=s[2],xy=list(g.ctr(D.cells[s[1]])))for s in ss if s[0]=='i'];outs.append(dict(net_id=ni,signal=sig,fanout=len(ss),sink_types=dict(Counter(s['kind']for s in sinks)),sinks=sinks))
 rows.append(dict(name=name,id=i,master=c[1],xy=list(g.ctr(c)),box=list(c[2:6]),inputs=ins,outputs=outs))
p=next(p for p in D.pins if p['name']=='cland_fstart_in_u1_i');q=deque([D.pin_net[p['k']]]);seen=set();comb=set();ff=set();clock_edges=[]
while q:
 ni=q.popleft()
 if ni in seen:continue
 seen.add(ni)
 for s in D.nets[ni][2]:
  if s[0]!='i':continue
  if s[2]:clock_edges.append(D.cells[s[1]][6]);continue
  i=s[1];k=D.kind(i)
  if k=='S':ff.add(i)
  elif i not in comb:comb.add(i);q.extend(D.drives.get(i,[]))
res=dict(scope='READONLY exact current5GRT START DATA cone/pose census, no CAD/source/clock/FF/cycle edits',start_pin=p,comb_count=len(comb),first_FF_count=len(ff),clock_sink_edges=clock_edges,path_cells=rows,comb_members=[dict(name=D.cells[i][6],kind=D.kind(i),master=D.cells[i][1],xy=list(g.ctr(D.cells[i])))for i in sorted(comb)],first_FFs=[dict(name=D.cells[i][6],xy=list(g.ctr(D.cells[i])))for i in sorted(ff)]);(P/'census.json').write_text(json.dumps(res,indent=1)+'\n')
print('cone',len(comb),'FF',len(ff),'clock',clock_edges)
for r in rows:print(r['name'],r['master'],r['xy'],[(x['net_id'],x['fanout'],x['sink_types'])for x in r['outputs']])

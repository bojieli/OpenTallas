"""Canonical 2417-pair field geometry and explicit irregular street roadmap.
Frame reservations are virtual; only real child boxes block station placement.
Roadmap edges use local horizontal streets and the real47.52um return subcolumns.
"""
import hashlib,json,heapq
from pathlib import Path

def load(path,root):
 p=Path(path);p=p if p.is_absolute() else root/p;d=json.loads(p.read_text())
 assert d['pair_count']==2417 and d['bf_pairs']==519 and d['root_count']==128
 fs={f['root']:f for f in d['placements']};assert sorted(fs)==list(range(128))
 stagepath=root/'results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json'
 stage=json.loads(stagepath.read_text());bf=set(stage['BF_site_IDs']);bounds=stage['region_bounds']
 assert len(bf)==519 and bounds==[r*2417//128 for r in range(129)]
 assert stage['PHW_required_by_stage'][:74]==[10]*74
 for r,f in fs.items():assert f['pairs']==bounds[r:r+2]
 d.update(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),frames=fs,bf_ids=bf,stage_map_sha256=hashlib.sha256(stagepath.read_bytes()).hexdigest())
 return d

def geometry(G,d,legacy_order):
 cols=sorted(d['columns'],key=lambda c:c['x_um']);mid=(cols[10]['x_um']+cols[11]['x_um'])/2
 out={}
 for ci,c in enumerate(cols):
  fs=sorted((f for f in d['placements'] if abs(f['origin_um'][0]-c['x_um'])<1e-6),key=lambda f:f['origin_um'][1])
  previous=c['y0_um']
  for ordinal,f in enumerate(fs):
   r=f['root'];x,y=f['origin_um'];lh,lt,lc=legacy_order[r]
   out[r]=dict(half='W' if x<mid else 'E',tier=ordinal,col=10-ci if ci<11 else ci-11,x=x,y=y,h=f['height_um'],
    logical_half=lh,logical_tier=lt,logical_col=lc,street=[x,previous,x+G.COL_W8,y],column_index=ci,
    cfifo_y=y-(G.PQ_ROOT_ROW if G.PQ_ROOTS else 0)-4.32-G.CF_WH[1])
   assert y-previous>=d['interframe_channels_um']['first']-1e-6
   previous=y+f['height_um']
 return out

def corridors(G,m,cor):
 """Real search regions; occupied nodes/ROMs/relays remain in Placer.occ."""
 d=m['canonical_layout'];fs=m['frames']
 # Never advertise obsolete fullwidth tier streets as free space.
 for k in list(cor):
  if k.startswith('ch') and k[2:].isdigit():del cor[k]
 for r,f in fs.items():
  x,a,x1,b=f['street'];cor[f'cfstreet{r}']=(x+.432,a+.432,x1-.432,b-.432)
 for i,c in enumerate(d['columns']):
  x=c['x_um']+G.LANES_W+G.NS_W
  cor[f'rsclane{i}']=(x+.432,c['y0_um']+.432,c['x_um']+G.COL_W8-.432,c['y1_um']-.432)
 return cor

class Roadmap:
 def __init__(self,G,m,cor):
  self.G,self.m,self.cor=G,m,cor;self.graph={};self.rootnode={};self.entry={}
  cols=sorted(m['canonical_layout']['columns'],key=lambda c:c['x_um'])
  self.cols=cols;levels={i:set() for i in range(22)};streets={i:[] for i in range(22)}
  self.sx={i:c['x_um']+G.COL_W8-G.RSC_W/2 for i,c in enumerate(cols)}
  for r,f in m['frames'].items():
   a=f['street'][1];b=f['street'][3]
   # Broadcast and returns use separate rows inside the actual local street.
   for kind,off in [('x',64.8+15),('r',8.64+20)]:
    y=a+off;assert y<b-4.32,(r,kind,a,b)
    streets[f['column_index']].append((r,kind,y));levels[f['column_index']].add(y)
  # Crossing column i horizontally at one of its own streets connects its
  # right-hand RSC lane with the preceding column's RSC lane. The small seam
  # is traversed by a wire, never assumed to fit a station.
  for i,rows in streets.items():
   for r,k,y in rows:
    self.rootnode[(r,k)]=(self.sx[i],y)
    if i not in (0,11):levels[i-1].add(y)
  for i,ys in levels.items():
   ys=sorted(ys)
   for a,b in zip(ys,ys[1:]):self.add((self.sx[i],a),(self.sx[i],b))
  for i,rows in streets.items():
   for r,k,y in rows:
    if i not in (0,11):self.add((self.sx[i-1],y),(self.sx[i],y))
    if i in (10,11):
     side='W' if i==10 else 'E';sx=G.s14_x(m,side,'xdn')
     entry=(sx,y);self.add(entry,(self.sx[i],y));self.entry.setdefault(side,[]).append(entry)
 def add(self,a,b):
  self.graph.setdefault(a,{})[b]=abs(a[0]-b[0])+abs(a[1]-b[1]);self.graph.setdefault(b,{})[a]=self.graph[a][b]
 def to_root(self,side,source,r,kind):
  target=self.rootnode[(r,kind)];q=[];dist={};prev={}
  stem=[source]
  if side=='E' and source[0] < self.m['geo']['x_fe']:
   cy=self.G.corr_y(self.m, 'xdn' if kind=='x' else 'r0')
   sx=self.entry[side][0][0]
   stem += [(source[0],cy),(sx,cy)]
  base=stem[-1]
  for node in self.entry[side]:
   d=abs(node[0]-base[0])+abs(node[1]-base[1]);dist[node]=d;prev[node]=None;heapq.heappush(q,(d,node))
  while q:
   d,n=heapq.heappop(q)
   if d!=dist[n]:continue
   if n==target:break
   for b,w in self.graph[n].items():
    nd=d+w
    if nd<dist.get(b,float('inf')):dist[b]=nd;prev[b]=n;heapq.heappush(q,(nd,b))
  assert target in dist,('canonical corridor graph disconnected',r,side)
  ns=[];n=target
  while n is not None:ns.append(n);n=prev[n]
  ns.reverse();return self.G._dedup(stem+[(ns[0][0],base[1])]+ns)

def trunks(G,m,CH,cor,starts,ga,end_spec,hub_block,bus):
 """Actual per-root chains, preserving immutable logical gather lane ordering.
 Geometry-independent equal-delay assertions are deliberately absent: actual
 x_stages/r_stages become compiler inputs, never an ideal tier flight estimate.
 """
 road=Roadmap(G,m,cor);allowed=[v for k,v in cor.items() if k.startswith(('cfstreet','rsclane','s14','vch','hcc'))]
 m['chain_paths']=[];calendar={}
 for r,f in sorted(m['frames'].items()):
  st=starts[f['half']];src=(st.x+st.w/2,st.y+st.h/2);path=road.to_root(f['half'],src,r,'x')
  cf=next(i for i in m['insts'] if i.name==f'cf{r}');end=(cf.x+cf.w/2,f['street'][1]+79.8)
  path=G._dedup(path+[(end[0],path[-1][1]),end])
  sts=CH.run(f'cx{r}',[G.LSW+2],path,allowed,src,forced=[G._poly_len(path)])
  assert sts,('canonical x chain has no actual station',r)
  G.chain_nets(CH,f'cx{r}',(st.name,'fo','od'),[i for i,_,_ in sts],[G.LSW+2]);last=sts[-1][0]
  if G.CFIFO_FALL:
   G._add_tap(m,last,0,(cf.name,None,'xd'));bus(f'cx{r}_fn','fclk',1,[(last.name,'fn0'),(cf.name,'xf')])
  else:G._add_tap(m,last,0,(cf.name,'xf','xd'))
  m.setdefault('x_stages',{})[r]=len(sts);calendar[r]={'root':r,'x_stations':len(sts),'x_path_um':G._poly_len(path),'physical_half':f['half'],'logical_gather':[f['logical_half'],f['logical_tier'],f['logical_col']]}
 for half in 'WE':
  for t in range(G.TIERS):
   roots=sorted((r for r,f in m['frames'].items() if f['logical_half']==half and f['logical_tier']==t),key=lambda r:m['frames'][r]['logical_col'],reverse=True)
   n=len(roots);gy=ga.y+ga.h*(.15+.7*t/(G.TIERS-1));nm,w,h=end_spec('m2l',[G.CRET]*n,'vr')
   endb=hub_block(f'hr_{half}{t}',nm,'hend',w,h,ga.x if half=='W' else ga.x+ga.w,gy,half,[cor['s14W'] if half=='W' else cor['vch']])
   for lane,r in enumerate(roots):
    f=m['frames'][r];cf=next(i for i in m['insts'] if i.name==f'cf{r}');src=(cf.x+cf.w/2,f['street'][1]+28.64)
    anchor=(G.s14_x(m,f['half'],f'r{t}'),endb.y+endb.h/2)
    path=list(reversed(road.to_root(f['half'],anchor,r,'r')));path=G._dedup([src,(path[0][0],src[1])]+path)
    # Crossing a physical/logical half uses the actual HC corridor and VCH.
    dst=(endb.x+endb.w/2,endb.y+endb.h/2)
    if f['half']!=half:
     cy=G.corr_y(m,f'r{t}');path +=[(path[-1][0],cy),(G.vch_x(m,f'r{t}'),cy),(G.vch_x(m,f'r{t}'),dst[1])]
    path=G._dedup(path+[(path[-1][0],dst[1]),dst])
    sts=CH.run(f'cr{r}',[G.CRET+2],path,allowed,src)
    G.chain_nets(CH,f'cr{r}',(cf.name,'rf','rd'),[i for i,_,_ in sts],[G.CRET+2]);last=(sts[-1][0].name,'fo0','do0') if sts else (cf.name,'rf','rd')
    bus(f'cr{r}_fe','fclk',1,[(last[0],last[1]),(endb.name,f'fi{lane}')]);bus(f'cr{r}_de','lane',G.CRET+2,[(last[0],last[2]),(endb.name,f'di{lane}')])
    m.setdefault('r_stages',{})[r]=len(sts);calendar[r].update(return_stations=len(sts),return_path_um=G._poly_len(path),gather_input_lane=lane)
   G._local_chain(m,CH,[cor['s14W'] if half=='W' else cor['vch']],endb,'o',ga,f'r{half}{t}',n*(G.CRET+1)+2,f'hr_{half}{t}_o','stream_1p2')
 m['canonical_calendar']=[calendar[r] for r in sorted(calendar)]

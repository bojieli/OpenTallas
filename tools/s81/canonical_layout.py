"""Canonical 2417-pair field geometry and explicit irregular street roadmap.
Frame reservations are virtual; only real child boxes block station placement.
Roadmap edges use local horizontal streets and the real47.52um return subcolumns.
"""
import hashlib,json,heapq
from pathlib import Path

def west_count(d):
 """Columns W of the hub (the widest gap between consecutive field columns; 11 on the 22-column die)."""
 xs=sorted(c['x_um'] for c in d['columns']);gaps=[b-a for a,b in zip(xs,xs[1:])]
 return gaps.index(max(gaps))+1

def load(path,root):
 p=Path(path);p=p if p.is_absolute() else root/p;d=json.loads(p.read_text())
 assert d['root_count']==128
 fs={f['root']:f for f in d['placements']};assert sorted(fs)==list(range(128))
 # wide-hub records (S-DIE 10-15) name their allocator stage map; the 22-column record uses the released binding
 stagepath=root/d.get('stage_map','results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json')
 stage=json.loads(stagepath.read_text());bf=set(stage['BF_site_IDs']);bounds=stage['region_bounds']
 assert len(bf)==d['bf_pairs'] and bounds[-1]==d['pair_count'] and len(bounds)==129
 if 'stage_map' not in d:
  assert d['pair_count']==2417 and d['bf_pairs']==519 and bounds==[r*2417//128 for r in range(129)]
  assert stage['PHW_required_by_stage'][:74]==[10]*74
 d['west_columns']=west_count(d)
 for r,f in fs.items():
  assert f['pairs']==bounds[r:r+2]
  assert sorted(e[0] for e in f['packed_elements'])==list(range(*f['pairs']))
  assert all((e[1]=='BF')==(e[0] in bf) for e in f['packed_elements'])
 cols=sorted(d['columns'],key=lambda c:c['x_um'])
 for access in d.get('service_access_corridors',[]):
  left,right=access['between_columns'];assert right==left+1
  x0,y0,x1,y1=access['rect_um']
  assert x0>=cols[left]['x_um']+next(f['outline_um'][0] for f in fs.values() if abs(f['origin_um'][0]-cols[left]['x_um'])<1e-6)-.001
  assert x1<=cols[right]['x_um']+.001 and x0<x1 and y0<y1
 stagehash=hashlib.sha256(stagepath.read_bytes()).hexdigest()
 assert d['source_pins'][str(stagepath.relative_to(root))]==stagehash
 d.update(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),frames=fs,bf_ids=bf,stage_map_sha256=hashlib.sha256(stagepath.read_bytes()).hexdigest())
 return d

def geometry(G,d,legacy_order):
 cols=sorted(d['columns'],key=lambda c:c['x_um']);nw=d['west_columns'];mid=(cols[nw-1]['x_um']+cols[nw]['x_um'])/2
 out={}
 for ci,c in enumerate(cols):
  fs=sorted((f for f in d['placements'] if abs(f['origin_um'][0]-c['x_um'])<1e-6),key=lambda f:f['origin_um'][1])
  previous=c['y0_um']
  for ordinal,f in enumerate(fs):
   r=f['root'];x,y=f['origin_um'];lh,lt,lc=legacy_order[r]
   assert abs(f['outline_um'][0]-G.COL_W8)<.025,('canonical frame width/source mismatch',r)
   out[r]=dict(half='W' if x<mid else 'E',tier=ordinal,col=nw-1-ci if ci<nw else ci-nw,x=x,y=y,h=f['height_um'],
    logical_half=lh,logical_tier=lt,logical_col=lc,street=[x,previous,x+G.COL_W8,y],column_index=ci,
    cfifo_y=y-(G.PQ_ROOT_ROW if G.PQ_ROOTS else 0)-4.32-G.CF_WH[1])
   assert y-previous>=d['interframe_channels_um']['first']-1e-6
   previous=y+f['height_um']
 return out

def corridors(G,m,cor):
 """Real search regions; occupied nodes/ROMs/relays remain in Placer.occ."""
 d=m['canonical_layout'];fs=m['frames']
 # Symmetric empty IO exclusions are absent from the canonical die. Keep
 # actual placed PHY/service boxes and supplemental homes as blockers.
 for key in ('s14W','s14E','vch','edgeW','edgeE'):
  xx0,_yy0,xx1,_yy1=cor[key];cor[key]=(xx0,20.432,xx1,G.DIE[1]-20.432)
 # Never advertise obsolete fullwidth tier streets as free space.
 for k in list(cor):
  if k.startswith('ch') and k[2:].isdigit():del cor[k]
 for r,f in fs.items():
  x,a,x1,b=f['street'];cor[f'cfstreet{r}']=(x+.432,a+.432,x1-.432,b-.432)
 for i,c in enumerate(d['columns']):
  x=c['x_um']+G.LANES_W+G.NS_W
  cor[f'rsclane{i}']=(x+.432,c['y0_um']+.432,c['x_um']+G.COL_W8-.432,c['y1_um']-.432)
 for access in d.get('service_access_corridors',[]):
  rect=tuple(access['rect_um']);assert len(rect)==4 and rect[0]<rect[2] and rect[1]<rect[3]
  cor['svc_access_'+access['name']]=rect
 return cor

class Roadmap:
 def __init__(self,G,m,cor,return_lanes=False):
  self.G,self.m,self.cor=G,m,cor;self.graph={};self.rootnode={};self.entry={}
  cols=sorted(m['canonical_layout']['columns'],key=lambda c:c['x_um'])
  self.cols=cols;nw=m['canonical_layout']['west_columns'];self.nw=nw
  levels={i:set() for i in range(len(cols))};streets={i:[] for i in range(len(cols))}
  self.sx={i:c['x_um']+G.COL_W8-(15.12 if return_lanes else G.RSC_W/2) for i,c in enumerate(cols)}
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
    if i not in (0,nw):levels[i-1].add(y)
  for i,ys in levels.items():
   ys=sorted(ys)
   for a,b in zip(ys,ys[1:]):self.add((self.sx[i],a),(self.sx[i],b))
  for i,rows in streets.items():
   for r,k,y in rows:
    if i not in (0,nw):self.add((self.sx[i-1],y),(self.sx[i],y))
    if i in (nw-1,nw):
     side='W' if i==nw-1 else 'E';sx=G.s14_x(m,side,'xdn')
     # A coherent field-column move may consume part of the old S14.
     # Keep the actual global spine outside the moved child strip, with
     # enough half-width for a real1026-bit vertical service station.
     if side=='W':sx=max(sx,cols[i]['x_um']+G.COL_W8+G.stn_dims([1026],False)[0]/2+.864)
     entry=(sx,y);self.add(entry,(self.sx[i],y));self.entry.setdefault(side,[]).append(entry)
  # Optional coherent column moves may open a real broad service gap.
  # Connect it only through the adjacent actual frame streets, never
  # through a virtual frame reservation or occupied ROM bank.
  for access in m['canonical_layout'].get('service_access_corridors',[]):
   x0,y0,x1,y1=access['rect_um'];sx=(x0+x1)/2;nodes=set()
   for ci in access['between_columns']:
    for r,kind,yy in streets[ci]:
     if y0<=yy<=y1:
      node=(sx,yy);nodes.add(node);self.add(node,self.rootnode[(r,kind)])
   ordered=sorted(nodes,key=lambda node:node[1])
   for a,b in zip(ordered,ordered[1:]):self.add(a,b)
 def add(self,a,b):
  self.graph.setdefault(a,{})[b]=abs(a[0]-b[0])+abs(a[1]-b[1]);self.graph.setdefault(b,{})[a]=self.graph[a][b]
 def to_root(self,side,source,r,kind):
  target=self.rootnode[(r,kind)];q=[];dist={};prev={}
  stem=[source]
  if side=='E' and source[0] < self.m['geo']['x_fe']:
   cy=self.G.corr_y(self.m, 'xdn' if kind=='x' else 'r0')
   sx=self.entry[side][0][0]
   stem += [(source[0],cy),(sx,cy)]
  elif side=='W' and self.G.wide_hub() and source[0] > self.G.wide_hub()['s14w'][1]:
   # wide hub: hub sources leave W through the W strip and the W corridor above MIX4 (SU / VM / MIX4 below)
   cy=self.G.wide_corr_y(self.m, 'xdn' if kind=='x' else 'r0')
   sx=self.entry[side][0][0];vx=self.G.wide_strip_x(self.m, 'xdn' if kind=='x' else 'r0')
   stem += [(vx,source[1]),(vx,cy),(sx,cy)] if source[0]>vx else [(source[0],cy),(sx,cy)]
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

def service_path(G,m,cor,hub_point,service_point,side):
 """Reach the real service face via actual irregular streets and S14.
 No symmetric shoreline strip is presumed empty in a canonical layout.
 """
 road=Roadmap(G,m,cor,return_lanes=True)
 for half in 'WE':
  entries=sorted(road.entry[half],key=lambda n:n[1])
  for a,b in zip(entries,entries[1:]):road.add(a,b)
 rsc_x=set(road.sx.values())
 for node,edges in road.graph.items():
  for nxt,length in list(edges.items()):
   if node[0]==nxt[0] and node[0] in rsc_x:edges[nxt]=2*length
 px,py=service_point
 def score(item):
  r,f=item;x0,y0,x1,y1=f['street']
  distance=max(x0-px,0,px-x1)+max(y0-py,0,py-y1)
  return distance,G._mh(road.rootnode[(r,'x')],service_point),r
 r,f=min(((r,f)for r,f in m['frames'].items() if f['half']==side),key=score)
 path=road.to_root(side,hub_point,r,'x');end=path[-1]
 # The last two legs stay within the selected actual service-facing street
 # except the explicit short access to the service port. Placer and the
 # independent exact-pin gate judge every physical access stage.
 path=G._dedup(path+[(px,end[1]),service_point])
 m.setdefault('canonical_service_paths',[]).append(dict(side=side,street_root=r,path=path,service_access_um=score((r,f))[0],physical_qualified=False))
 return path

def compact_return_relays(G,m,CH):
 """Pack existing RSC return relays west; retain IDs, ports and all stages.
 Four70-bit forwarded lanes need28.056um, versus41.016 for six. A17.256um
 existing relay plus the four-lane station and .432um gaps fits47.52um.
 This only moves actual wholly-contained RSC relays; every candidate is
 tested against all real occupied boxes before its position changes.
 """
 candidates=[];regions={f'frame_{r}' for r in m['frames']}
 for obj in m['insts']:
  if not obj.name.startswith('y_rt_') or obj.region not in regions:continue
  r=int(obj.region[6:]);f=m['frames'][r];left=f['x']+G.LANES_W+G.NS_W;right=f['x']+G.COL_W8
  if obj.x>=left-.001 and obj.x+obj.w<=right+.001:
   nx=G.up(left+.432,G.GX)
   if nx<obj.x-.001:candidates.append((obj,nx))
 moving={obj.name for obj,_ in candidates};occ=G.Occ()
 for obj in m['insts']:
  if obj.name not in moving:occ.add(obj.box())
 receipt=[]
 for obj,nx in candidates:
  old=obj.x;box=(nx,obj.y,nx+obj.w,obj.y+obj.h)
  if occ.free(box,.432):obj.x=nx
  else:assert occ.free(obj.box(),.432),('canonical relay repack collision',obj.name)
  occ.add(obj.box());receipt.append(dict(inst=obj.name,old_x=old,new_x=obj.x,y=obj.y,w=obj.w,h=obj.h,moved=obj.x!=old))
 CH.P.occ=occ
 m['canonical_rsc_repack']=dict(return_bundle_lanes=4,station_width_um=G.stn_dims([G.CRET+2]*4,False)[0],moves=receipt,physical_qualified=False)

def trunks(G,m,CH,cor,starts,ga,end_spec,hub_block,bus):
 """Actual per-root chains, preserving immutable logical gather lane ordering.
 Geometry-independent equal-delay assertions are deliberately absent: actual
 x_stages/r_stages become compiler inputs, never an ideal tier flight estimate.
 """
 compact_return_relays(G,m,CH)
 road=Roadmap(G,m,cor);allowed=[v for k,v in cor.items() if k.startswith(('cfstreet','rsclane','s14','vch','hcc','svc_access','hub_w','strip_w'))]
 m['chain_paths']=[];calendar={};m['canonical_injectors']={side:dict(inst=starts[side].name,box=list(starts[side].box()),source_ports=['fo','od'])for side in 'WE'}
 m['canonical_broadcast_trees']={}
 # One real broadcast tree per physical half. Shared road prefixes are
 # registered once; independent per-root chains would replicate the same
 # 566-bit stream until the narrow RSC lane is full (measured cx37 failure).
 for side in 'WE':
  st=starts[side];source=(st.x+st.w/2,st.y+st.h/2)
  entries=sorted(road.entry[side],key=lambda n:n[1])
  for a,b in zip(entries,entries[1:]):road.add(a,b)
  # Entry candidates include return rows; take an actual x-row as tree root.
  xentries=[road.rootnode[(r,'x')] for r,f in m['frames'].items() if f['column_index']==(road.nw-1 if side=='W' else road.nw)]
  root=min(xentries,key=lambda n:abs(n[1]-source[1]))
  entry=next(n for n in entries if n[1]==root[1])
  override=m['canonical_layout'].get('broadcast_entry_overrides',{}).get(side)
  if override is not None:
   assert len(override)==2
   entry=min(entries,key=lambda n:G._mh(n,override))
   assert G._mh(entry,override)<.001,('broadcast override is not an actual S14 entry',side,override,entry)
  if side=='E':
   cy=G.corr_y(m,'xdn');prefix=G._dedup([source,(source[0],cy),(entry[0],cy),entry])
  elif G.wide_hub():
   # wide hub: up the W strip to the W corridor above MIX4, then W to the S14W entry
   cy=G.wide_corr_y(m,'xdn');prefix=G._dedup([source,(source[0],cy),(entry[0],cy),entry])
  else:prefix=G._dedup([source,(entry[0],source[1]),entry])
  dist={entry:0};parent={entry:None};q=[(0,entry)]
  while q:
   cost,n=heapq.heappop(q)
   if cost!=dist[n]:continue
   for nxt,wgt in road.graph[n].items():
    if nxt[0] < m['geo']['x_sp'] and side=='E' or nxt[0] > m['geo']['x_fe'] and side=='W':continue
    nc=cost+wgt
    if nc<dist.get(nxt,float('inf')):dist[nxt]=nc;parent[nxt]=n;heapq.heappush(q,(nc,nxt))
  required=set()
  for r,f in m['frames'].items():
   if f['half']!=side:continue
   n=road.rootnode[(r,'x')]
   while n is not None:required.add(n);n=parent[n]
  m['canonical_broadcast_trees'][side]=dict(injector=st.name,prefix=prefix,entry=entry,root_targets={r:road.rootnode[(r,'x')] for r,f in m['frames'].items() if f['half']==side},edges=[dict(node=n,parent=parent[n],chain=f'cx{side}_edge{k}')for k,n in enumerate(sorted(required-{entry},key=lambda n:dist[n]))])
  pair=bool(getattr(G,'BF_X2_PAIR',False))
  # --bf-x2-pair (S-BIND r6): the packed static word as two forwarded lanes of one epoch -- A = {legacy 564, v, rst_n}
  # (the historical 566-b lane, its street spots) and B = {x2 536, v, rst_n} -- B's stations are FORCED at A's station
  # positions on every chain, so both lanes have identical station counts (asserted) and reach the column ingress pair
  # on the same edge; one 1,102-b station (58.3 x 17.3 um) found no street spot (bind6/bind10 cxW_edge27)
  LA=[G.X0B+G.X1B+G.CCB+2] if pair else [G.LSW+2];LB=[G.X2B+2]
  def run_pair(name,path,src,forced,srcA,srcB):
   sa=CH.run(name,LA,path,allowed,src,forced=forced)
   G.chain_nets(CH,name,srcA,[i for i,_,_ in sa],LA)
   tA=(sa[-1][0].name,'fo0','do0') if sa else srcA
   if not pair:return sa,tA,None
   sb=CH.run(name+'_x2',LB,path,allowed,src,forced=sorted(set([round(s_,3) for _,s_,_ in sa]+list(forced))))
   assert len(sb)==len(sa),('--bf-x2-pair: unequal station counts',name,len(sa),len(sb))
   G.chain_nets(CH,name+'_x2',srcB,[i for i,_,_ in sb],LB)
   return sa,tA,(sb[-1][0].name,'fo0','do0') if sb else srcB
  rootsource=(st.name,'fo','oa' if pair else 'od');rootB=(st.name,'fo2','ob');tail={};tailB={};flight={};loc={}
  pre,tail[entry],tailB[entry]=run_pair(f'cx{side}_spine',prefix,source,[G._poly_len(prefix)],rootsource,rootB)
  loc[entry]=(pre[-1][0].x+pre[-1][0].w/2,pre[-1][0].y+pre[-1][0].h/2) if pre else source;flight[entry]=len(pre)
  for k,n in enumerate(sorted(required-{entry},key=lambda n:dist[n])):
   par=parent[n];src=loc[par];path=G._dedup([src,(par[0],src[1]),par,n]);name=f'cx{side}_edge{k}'
   sts,tail[n],tailB[n]=run_pair(name,path,src,[G._poly_len(path)],tail[par],tailB[par])
   loc[n]=(sts[-1][0].x+sts[-1][0].w/2,sts[-1][0].y+sts[-1][0].h/2) if sts else src;flight[n]=flight[par]+len(sts)
  for r,f in sorted(m['frames'].items()):
   if f['half']!=side:continue
   n=road.rootnode[(r,'x')];cf=next(i for i in m['insts'] if i.name==f'cf{r}');src=loc[n];end=(cf.x+cf.w/2,f['street'][1]+79.8)
   path=G._dedup([src,(end[0],src[1]),end])
   sts,tA,tB=run_pair(f'cx{r}',path,src,[G._poly_len(path)],tail[n],tailB[n])
   last=next(i for i in m['insts'] if i.name==tA[0])
   if G.CFIFO_FALL:
    G._add_tap(m,last,0,(cf.name,None,'xd'));bus(f'cx{r}_fn','fclk',1,[(last.name,'fn0'),(cf.name,'xf')])
   else:G._add_tap(m,last,0,(cf.name,'xf','xd'))
   if pair:
    lb=next(i for i in m['insts'] if i.name==tB[0])
    assert lb.kind=='stn' or lb.name==st.name,('--bf-x2-pair: x2 lane tail',r,lb.name)
    if G.CFIFO_FALL:
     G._add_tap(m,lb,0,(cf.name,None,'xd2'));bus(f'cx{r}_fn2','fclk',1,[(lb.name,'fn0'),(cf.name,'xf2')])
    else:G._add_tap(m,lb,0,(cf.name,'xf2','xd2'))
   count=flight[n]+len(sts);m.setdefault('x_stages',{})[r]=count
   calendar[r]={'root':r,'x_stations':count,'x_path_um':G._poly_len(prefix)+dist[n]+G._poly_len(path),'physical_half':side,'logical_gather':[f['logical_half'],f['logical_tier'],f['logical_col']]}
 # Return stations occupy the eastern RSC lane beside existing packed relays.
 road=Roadmap(G,m,cor,return_lanes=True)
 # Global returns must climb in the existing broad S14 spine, rather than
 # concentrating every gather group in the innermost47.52um field column.
 # All street entries are physically connected by that actual spine.
 for side in 'WE':
  entries=sorted(road.entry[side],key=lambda n:n[1])
  for a,b in zip(entries,entries[1:]):road.add(a,b)
 # Optimize routing preference only; physical length, station reach and
 # flight counts still come from each emitted real polyline and primitive.
 rsc_x=set(road.sx.values())
 for node,edges in road.graph.items():
  for nxt,length in list(edges.items()):
   if node[0]==nxt[0] and node[0] in rsc_x:edges[nxt]=2*length
 m['canonical_return_topology']='local streets to external S14 spine; field RSC vertical cost2, actual geometry unchanged'
 for logical in 'WE':
  for t in range(G.TIERS):
   roots=sorted((r for r,f in m['frames'].items() if f['logical_half']==logical and f['logical_tier']==t),key=lambda r:m['frames'][r]['logical_col'],reverse=True)
   n=len(roots);gy=ga.y+ga.h*(.15+.7*t/(G.TIERS-1));nm,w,h=end_spec('m2l',[G.CRET]*n,'vr')
   endb=hub_block(f'hr_{logical}{t}',nm,'hend',w,h,ga.x if logical=='W' else ga.x+ga.w,gy,logical,[cor['s14W'] if logical=='W' else cor['vch']])
   for side in 'WE':
    members=[(lane,r) for lane,r in enumerate(roots) if m['frames'][r]['half']==side]
    # Four lanes leave space beside17.256um existing field-return relays.
    for batch in range(0,len(members),4):
     group=members[batch:batch+4];prefix=f'cr{logical}{t}_{side}{batch//4}'
     entry=min(road.entry[side],key=lambda n:abs(n[1]-gy))
     dist={entry:0};parent={entry:None};q=[(0,entry)]
     while q:
      cost,node=heapq.heappop(q)
      if cost!=dist[node]:continue
      for nxt,wgt in road.graph[node].items():
       nc=cost+wgt
       if nc<dist.get(nxt,float('inf')):dist[nxt]=nc;parent[nxt]=node;heapq.heappush(q,(nc,nxt))
     needed=set();flows={};flights={r:0 for _,r in group}
     def advance(name,path,active):
      ordered=sorted(active);positions=[byname[active[j][0]] for j in ordered]
      src=(sum(i.x+i.w/2 for i in positions)/len(positions),sum(i.y+i.h/2 for i in positions)/len(positions))
      path=G._dedup([src,(path[0][0],src[1])]+path)
      stages=CH.run(name,[G.CRET+2]*len(ordered),path,allowed,src,forced=[G._poly_len(path)])
      for k,(obj,_s,_hop) in enumerate(stages):
       byname[obj.name]=obj
       for j,lane in enumerate(ordered):
        old=active[lane];bus(f'{name}_f{k}_{j}','fclk',1,[(old[0],old[1]),(obj.name,f'fi{j}')]);bus(f'{name}_d{k}_{j}','lane',G.CRET+2,[(old[0],old[2]),(obj.name,f'di{j}')])
        active[lane]=(obj.name,f'fo{j}',f'do{j}',old[3]);flights[old[3]]+=1
      return active
     byname={i.name:i for i in m['insts']}
     for lane,r in group:
      f=m['frames'][r];cf=byname[f'cf{r}'];node=road.rootnode[(r,'r')]
      spur=[(cf.x+cf.w/2,node[1]),node]
      active=advance(f'{prefix}_tap{r}',spur,{lane:(cf.name,'rf','rd',r)})
      flows.setdefault(node,{}).update(active)
      while node is not None:needed.add(node);node=parent[node]
     for k,node in enumerate(sorted(needed-{entry},key=lambda node:dist[node],reverse=True)):
      active=flows.pop(node);par=parent[node]
      active=advance(f'{prefix}_edge{k}',[node,par],active);flows.setdefault(par,{}).update(active)
     active=flows[entry];dst=(endb.x+endb.w/2,endb.y+endb.h/2);path=[entry]
     if side=='E':
      cy=G.corr_y(m,f'r{t}');vx=G.vch_x(m,f'r{t}');path +=[(entry[0],cy),(vx,cy)]
     elif G.wide_hub():
      # wide hub: W returns cross over SU / MIX4 in the W corridor, then drop down the W strip to the gather W face
      cy=G.wide_corr_y(m,f'r{t}');vx=G.wide_strip_x(m,f'r{t}');path +=[(entry[0],cy),(vx,cy)]
     if side!=logical:
      wx=G.s14_x(m,'W',f'r{t}');vx=G.vch_x(m,f'r{t}');xx0,xx1=sorted((wx,vx));margin=.432
      free=[(max(cor['s14W'][1],cor['vch'][1]),min(cor['s14W'][3],cor['vch'][3]))]
      if G.wide_hub():
       # wide hub: the halves meet across the capture column only (W strip <-> VCH), through a seam between its slabs
       wx=G.wide_strip_x(m,f'r{t}');xx0,xx1=sorted((wx,vx))
       # above the gather (not the pq-cnt seam), up to the W approach top: the free column above the host included
       free=[(max(cor['strip_w'][1],cor['vch'][1],ga.y+ga.h),min(cor['hub_w'][3],cor['vch'][3]))]
       sm_=G.wide_hub().get('vmhc_seam')
       if sm_:   # the VM <-> HC seam is reserved for those buses
        free=[iv for lo_,hi_ in free for iv in ((lo_,min(hi_,sm_[0]-20)),(max(lo_,sm_[1]+20),hi_)) if iv[1]>iv[0]]
      for obj in m['insts']:
       if obj.x>=xx1 or obj.x+obj.w<=xx0:continue
       cut=(obj.y-margin,obj.y+obj.h+margin);nfree=[]
       for lo,hi in free:
        if cut[1]<=lo or cut[0]>=hi:nfree.append((lo,hi));continue
        if cut[0]>lo:nfree.append((lo,cut[0]))
        if cut[1]<hi:nfree.append((cut[1],hi))
       free=nfree
      need=G.stn_dims([G.CRET+2]*len(active),True)[1]+2*margin
      gaps=[(lo,hi) for lo,hi in free if hi-lo>=need];assert gaps,('canonical W bundled crossing has no real gap',prefix,need)
      lo,hi=min(gaps,key=lambda ab:abs((ab[0]+ab[1])/2-dst[1]));yy=(lo+hi)/2
      allowed.append((xx0-20,lo,xx1+20,hi));endx=wx if logical=='W' else vx;path +=[(path[-1][0],yy),(endx,yy)]
      m.setdefault('canonical_w_crossings',[]).append(dict(bundle=prefix,roots=[r for _,r in group],gap_um=[lo,hi],crossing_y_um=yy,unqualified_cut=True))
     path=G._dedup(path+[(path[-1][0],dst[1]),dst]);active=advance(f'{prefix}_hub',path,active)
     for lane,r in group:
      tail=active[lane];bus(f'{prefix}_fe{lane}','fclk',1,[(tail[0],tail[1]),(endb.name,f'fi{lane}')]);bus(f'{prefix}_de{lane}','lane',G.CRET+2,[(tail[0],tail[2]),(endb.name,f'di{lane}')])
      m.setdefault('r_stages',{})[r]=flights[r];calendar[r].update(return_stations=flights[r],gather_input_lane=lane,return_bundle=prefix)
   G._local_chain(m,CH,([cor['s14W']]+([cor['strip_w'],cor['hub_w']] if G.wide_hub() else []) if logical=='W' else [cor['vch']]),endb,'o',ga,f'r{logical}{t}',n*(G.CRET+1)+2,f'hr_{logical}{t}_o','stream_1p2')
 m['canonical_calendar']=[calendar[r] for r in sorted(calendar)]


def trace_calendar(G,m):
 """Count actual emitted transport registers after hop fixes, by immutable root.
 Counts preserve separate forwarded half-edge and common-clock stages. Physical
 clock phases and endpoint FIFO latency remain unqualified, never inferred.
 """
 by={i.name:i for i in m['insts']};incoming={}
 for bid,cls,bits,eps in m['buses']:
  if not eps or cls in ('fclk','clock','col_clock','clock_trunk'):continue
  for name,port in eps[1:]:
   incoming.setdefault((name,G.pslice(port)[0]),[]).append((eps[0],bid))
 def trace(name,port,source):
  stages=[];seen=set()
  while name!=source:
   key=(name,G.pslice(port)[0]);choices=incoming.get(key,[])
   if key in seen or len(choices)!=1:return dict(status='UNRESOLVED',endpoint=key,drivers=len(choices),stages=stages)
   seen.add(key);(name,port),bid=choices[0]
   if name==source:break
   obj=by.get(name);base=G.pslice(port)[0]
   if obj is None:return dict(status='UNRESOLVED',endpoint=[name,port],stages=stages)
   if obj.kind=='stn' and base.startswith('do'):
    stages.append(dict(instance=name,master=obj.master,clock='forwarded',nominal_half_edges=1,bus=bid));port='di'+base[2:]
   elif obj.kind in ('rly','hstn') and base in ('o','dq'):
    stages.append(dict(instance=name,master=obj.master,clock='common',nominal_cycles=1,bus=bid));port='i' if base=='o' else 'di'
   else:return dict(status='UNRESOLVED',endpoint=[name,port],kind=obj.kind,stages=stages)
  return dict(status='COUNTED_NOT_PHASE_QUALIFIED',forwarded_stages=sum(x['clock']=='forwarded' for x in stages),common_stages=sum(x['clock']=='common' for x in stages),stages=stages)
 out=[]
 for row in m.get('canonical_calendar',[]):
  r=row['root'];f=m['frames'][r];half,t,_c=row['logical_gather'];lane=row['gather_input_lane']
  out.append(dict(root=r,x=trace(f'cf{r}','xd',f'hx_{row["physical_half"]}'),return_path=trace(f'hr_{half}{t}',f'di{lane}',f'cf{r}'),column=dict(slot_stations=f['last_slot']+1,bank_stages=f.get('bank_stages',0),return_tree_stages=f.get('ret_stages',0),x_relays=f.get('relay_x',0),return_relays=f.get('relay_ret',0)),fixed_phase_qualified=False))
 return dict(scope='Actual emitted register inventory after hop fixes; no ideal global-tier flight estimate. Clock phase, crossings and pin timing remain separate required gates.',roots=out)

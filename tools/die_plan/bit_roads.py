"""Exact indexed FT correspondence and conservative gcell road aggregation.

No bit is reassigned to another station. Aggregation is legal only for the same
stage, oriented grid edge and allowed-layer set; every member contributes one
track. Source, destination and all epoch/data indices must be present exactly.
"""
import collections,hashlib,math

INSET={'E':(-1.,0.),'W':(1.,0.),'N':(0.,-1.),'S':(0.,1.)}


def port_bit_points(P,part,pid):
 pr=P.ports[pid];face=pr['face'] if pr['src']['part']==part or pr['src']['part']=='@die' else {'E':'W','W':'E','N':'S','S':'N'}[pr['face']]
 r=P.rect(part);out={}
 for bit,layer,c in P.port_pins(pid):
  if bit in out:raise ValueError(f'{part}/{pid}: duplicate bit {bit}')
  x,y=((r[2] if face=='E' else r[0]),c) if face in 'EW' else (c,(r[3] if face=='N' else r[1]))
  dx,dy=INSET[face];out[bit]=(x+dx,y+dy)
 return out


def indexed_chains(P,part,slot,pin,pout,reach=405.):
 s=P.slot(part,slot);sites=s.get('bit_sites_um');k=int(s['stations']);n=int(s['width'])+1
 if sites is None or len(sites)!=k-1:raise ValueError(f'{part}/{slot}: missing explicit stages (need {k-1})')
 pi,po=port_bit_points(P,part,pin),port_bit_points(P,part,pout);expected=set(range(n))
 if set(pi)!=expected or set(po)!=expected:raise ValueError(f'{part}/{slot}: endpoint/epoch bit coverage does not match 0..{n-1}')
 if any(len(stage)!=n for stage in sites):raise ValueError(f'{part}/{slot}: station bit coverage does not match {n}')
 cw,ch=s['bit_site_cell_um'];chains={};worst=0.
 for bit in range(n):
  chain=[pi[bit]]+[tuple(P.to_die(part,(stage[bit][0]+cw/2,stage[bit][1]+ch/2))) for stage in sites]+[po[bit]]
  for stage,(a,b) in enumerate(zip(chain,chain[1:])):
   hop=abs(a[0]-b[0])+abs(a[1]-b[1]);worst=max(worst,hop)
   if hop>reach+1e-6:raise ValueError(f'{part}/{slot} bit {bit} hop {stage}: {hop:.6f}>{reach}')
  chains[bit]=chain
 return chains,dict(bits=n,stages=k,hops=n*k,max_hop_um=worst,epoch_included=True)


def aggregate(P,part,slot,pin,pout,grid,reach=405.):
 chains,stats=indexed_chains(P,part,slot,pin,pout,reach);groups={};raw_crossings=0;top=min(7,int(P.type_top_layer(P.parts[part]['type'])[1:]))
 for bit,chain in chains.items():
  for stage,(a,b) in enumerate(zip(chain,chain[1:])):
   # An actual L1 candidate on real H/V signal layers; no unpriced repeater.
   corner=(b[0],a[1])
   for a,b in [(a,corner),(corner,b)]:
    if abs(a[0]-b[0])+abs(a[1]-b[1])<1e-9:continue
    sl,horiz=grid.band(a,b,0.)
    raw_crossings += sl[2]-sl[0] if horiz else sl[3]-sl[1]
    allowed=tuple(l for l in (('M4','M6') if horiz else ('M5','M7')) if int(l[1:])<=top)
    if not allowed:raise ValueError(f'{part}/{slot}: no legal signal layer')
    key=(stage,horiz,tuple(sl),allowed);rec=groups.get(key)
    if rec is None:rec=groups[key]=dict(bits=0,stage=stage,horiz=horiz,sl=tuple(sl),allowed=allowed,bit_indices=[],segments_digest=hashlib.sha256(),actual_rect=[math.inf,math.inf,-math.inf,-math.inf])
    rec['bits']+=1;rec['bit_indices'].append(bit);rec['segments_digest'].update(repr((bit,stage,a,b)).encode());r=rec['actual_rect'];r[:]=[min(r[0],a[0],b[0]),min(r[1],a[1],b[1]),max(r[2],a[0],b[0]),max(r[3],a[1],b[1])]
 for rec in groups.values():rec['segments_digest']=rec['segments_digest'].hexdigest()
 grouped_crossings=sum(r['bits']*((r['sl'][2]-r['sl'][0]) if r['horiz'] else (r['sl'][3]-r['sl'][1])) for r in groups.values())
 assert grouped_crossings==raw_crossings
 stats.update(groups=len(groups),bit_segments=sum(x['bits'] for x in groups.values()),raw_track_cell_crossings=raw_crossings,grouped_track_cell_crossings=grouped_crossings)
 return list(groups.values()),stats


def candidates(a,b,box,reach,gcell):
 """Deterministic HV/VH/Z candidates; each stays in-part and within priced reach."""
 ax,ay=a;bx,by=b;seen=set()
 raw=[[a,(bx,ay),b],[a,(ax,by),b]]
 slack=max(0.,reach-abs(ax-bx)-abs(ay-by))/2
 for x in [(ax+bx)/2,min(ax,bx)-slack,max(ax,bx)+slack]:
  x=min(box[2]-1e-6,max(box[0]+1e-6,round(x/gcell)*gcell));raw.append([a,(x,ay),(x,by),b])
 for y in [(ay+by)/2,min(ay,by)-slack,max(ay,by)+slack]:
  y=min(box[3]-1e-6,max(box[1]+1e-6,round(y/gcell)*gcell));raw.append([a,(ax,y),(bx,y),b])
 # Remaining legal gcell spines use the same priced hop, not extra stations.
 for axis in (0,1):
  lo=min(a[axis],b[axis])-slack;hi=max(a[axis],b[axis])+slack;mid=(a[axis]+b[axis])/2
  coords=sorted((i*gcell for i in range(math.ceil(lo/gcell),math.floor(hi/gcell)+1)),key=lambda v:(abs(v-mid),v))
  for v in coords:
   if axis==0:
    if box[0]<v<box[2]:raw.append([a,(v,ay),(v,by),b])
   else:
    if box[1]<v<box[3]:raw.append([a,(ax,v),(bx,v),b])
 for points in raw:
  points=[p for i,p in enumerate(points) if not i or p!=points[i-1]];key=tuple(points)
  length=sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(points,points[1:]))
  if key not in seen and length<=reach+1e-6:seen.add(key);yield points,length


def plan(P,part,slot,pin,pout,grid,gcell,reach=405.,target=.6):
 """Select actual bit paths before build using real per-layer capacity/OBS.

Only legal M4-M7 layers are considered. A failure to meet target remains a
capacity FAIL; selecting a route never adds a register or changes bit identity.
"""
 chains,stats=indexed_chains(P,part,slot,pin,pout,reach);top=min(7,int(P.type_top_layer(P.parts[part]['type'])[1:]));groups={};route_max=0.;alternates=0;blocked=[];digest=hashlib.sha256();raw_crossings=0
 for bit,chain in chains.items():
  for stage,(a,b) in enumerate(zip(chain,chain[1:])):
   best=None
   for rank,(points,length) in enumerate(candidates(a,b,P.rect(part),reach,gcell)):
    chosen=[];peak=0.;bad=False
    for x,y in zip(points,points[1:]):
     if x==y:continue
     sl,horiz=grid.band(x,y,0.);layers=[l for l in (('M4','M6') if horiz else ('M5','M7')) if int(l[1:])<=top];win=None
     for layer in layers:
      add=grid.load(layer,sl,horiz,1)
      if add is None:continue
      use=grid.worst(layer,sl,add)
      if win is None or use<win[0]:win=(use,layer,add)
     if win is None:bad=True;break
     use,layer,add=win;peak=max(peak,use);grid.commit(layer,sl,add);chosen.append((layer,sl,horiz,add,x,y))
    # Undo speculative additions exactly (one-track increments are binary halves).
    for layer,sl,horiz,add,x,y in reversed(chosen):
     i0,j0,i1,j1=sl;grid.dem[layer][j0:j1,i0:i1]-=add
    if bad:continue
    score=(peak,length,rank)
    if best is None or score<best[0]:best=(score,chosen)
    if peak<=target:break
   if best is None:blocked.append(dict(bit=bit,stage=stage));continue
   (peak,length,rank),chosen=best;route_max=max(route_max,length);alternates+=rank!=0
   for layer,sl,horiz,add,x,y in chosen:
    grid.commit(layer,sl,add);raw_crossings+=sl[2]-sl[0] if horiz else sl[3]-sl[1]
    key=(stage,horiz,tuple(sl),layer);r=groups.get(key)
    if r is None:r=groups[key]=dict(bits=0,stage=stage,horiz=horiz,sl=tuple(sl),allowed=(layer,),selected_layer=layer,bit_indices=[],actual_rect=[math.inf,math.inf,-math.inf,-math.inf])
    r['bits']+=1;r['bit_indices'].append(bit);rr=r['actual_rect'];rr[:]=[min(rr[0],x[0],y[0]),min(rr[1],x[1],y[1]),max(rr[2],x[0],y[0]),max(rr[3],x[1],y[1])];digest.update(repr((bit,stage,layer,x,y)).encode())
 grouped=sum(r['bits']*((r['sl'][2]-r['sl'][0]) if r['horiz'] else (r['sl'][3]-r['sl'][1])) for r in groups.values());assert grouped==raw_crossings
 stats.update(groups=len(groups),bit_segments=sum(r['bits'] for r in groups.values()),raw_track_cell_crossings=raw_crossings,grouped_track_cell_crossings=grouped,max_planned_route_um=route_max,non_HV_hops=alternates,blocked_hops=blocked,planned_routes_sha256=digest.hexdigest())
 return list(groups.values()),stats

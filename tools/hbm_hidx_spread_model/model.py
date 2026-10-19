"""SOURCE MODEL ONLY: actual-native-cohort packing, no OpenROAD/ODB mutation.
The output is a proposed site plan, never an implemented placement checkpoint.
"""
import json,gzip,re,collections,math,itertools,hashlib,array
from pathlib import Path
P=Path(__file__).resolve().parents[1];I=P/'input';O=P/'out';O.mkdir(exist_ok=False)
pins=json.load(gzip.open(I/'native_pin_geometry.json.gz','rt'));old=json.loads((I/'positions.json').read_text());caps=json.load(gzip.open(I/'loaded_caps.json.gz','rt'));u=old['units']
site=round(.054*u);rowh=round(.270*u);corelo=round(2.16*u);bandlo=round(56.16*u)
clockcell=json.loads((I/'native_clock_cell.json').read_text());assert hashlib.sha256((I/'setRC.tcl').read_bytes()).hexdigest()=='ce6e29fe23b648839009c53035901066653d5850f9419ba85169c715b2cebd14'
cells=old['insts'];canonical={p['canonical_cell']:p['cell'] for p in pins['pins']};assert len(canonical)==11145
clocknets={p['net'] for p in pins['pins'] if p['role']=='CLOCK'};assert len(clocknets)==1
byname={p['canonical_cell']:p['cell'] for p in pins['pins']};co={};nets=collections.defaultdict(set);contacts={}
for p in pins['pins']:
 n=p['canonical_cell'];m=re.search(r'on\.(pair|quad|slice)\[(\d+)\]',n)
 if m:co[n]=f'{m[1]}[{int(m[2])}]'
 if p['role'] not in ['POWER','GROUND','CLOCK']:nets[p['net']].add(n)
 contacts[n,p['pin']]=p
canonical_count=len(co);assert canonical_count==8265
for _ in range(4):
 for ns in nets.values():
  known={co[n] for n in ns if n in co}
  if len(known)==1:
   for n in ns:co.setdefault(n,next(iter(known)))
assert len(co)==11145
portnets={p['net'] for p in pins['ports']}
assert all(len({co[n] for n in ns})==1 for net,ns in nets.items() if net not in portnets and net not in clocknets)
groups=collections.defaultdict(list)
for n,g in co.items():groups[g].append(n)
assert len(groups)==27
def width(n):z=cells[byname[n]]['bbox'];return (z[2]-z[0])//site
areas={g:sum(width(n)*.054*.270 for n in ns) for g,ns in groups.items()}
def center(shapes):
 # Largest native routing access rectangle, an actual point inside real metal.
 layer,b=max(shapes,key=lambda z:((z[1][2]-z[1][0])*(z[1][3]-z[1][1]),z[0],z[1]))
 return ((b[0]+b[2])/2/u,(b[1]+b[3])/2/u)
ports={p['port']:p for p in pins['ports']};anchors=collections.defaultdict(list);port_aliases={}
for net in caps['all_driver_nets']:
 drv=net['driver']
 if drv['cell'] is None and drv['pin'] not in ports:
  cs=net['contacts'];assert len(cs)==2904 and all(contacts[c['cell'],c['pin']]['role']=='CLOCK' for c in cs)
  ids={contacts[c['cell'],c['pin']]['net'] for c in cs};assert ids==clocknets
  actual=[p for p in pins['ports'] if p['net'] in ids];assert len(actual)==1
  ports[drv['pin']]=actual[0];port_aliases[drv['pin']]=actual[0]['port']
for net in caps['all_driver_nets']:
 drv=net['driver']
 if drv['cell'] is None and ports[drv['pin']]['net'] not in clocknets:
  xy=center(ports[drv['pin']]['shapes'])
  for c in net['contacts']:
   if c['cell'] is not None:anchors[co[c['cell']]].append((xy,max(c['cap'],.001)))
 for c in net['contacts']:
  if c['cell'] is None and drv['cell'] is not None:
   anchors[co[drv['cell']]].append((center(ports[c['pin']]['shapes']),c['cap']))
def anchorcost(g,xy):return sum(w*(abs(q[0]-xy[0])+abs(q[1]-xy[1])) for q,w in anchors[g])
def hungarian(cost):
 n=len(cost);assert all(len(r)==n for r in cost);uu=[0.]*(n+1);vv=[0.]*(n+1);pp=[0]*(n+1);way=[0]*(n+1)
 for ii in range(1,n+1):
  pp[0]=ii;j0=0;mins=[float('inf')]*(n+1);used=[False]*(n+1)
  while True:
   used[j0]=True;i0=pp[j0];delta=float('inf');j1=0
   for j in range(1,n+1):
    if not used[j]:
     cur=cost[i0-1][j-1]-uu[i0]-vv[j]
     if cur<mins[j]:mins[j]=cur;way[j]=j0
     if mins[j]<delta:delta=mins[j];j1=j
   for j in range(n+1):
    if used[j]:uu[pp[j]]+=delta;vv[j]-=delta
    else:mins[j]-=delta
   j0=j1
   if pp[j0]==0:break
  while True:
   j1=way[j0];pp[j0]=pp[j1];j0=j1
   if j0==0:break
 result=[None]*n
 for j in range(1,n+1):result[pp[j]-1]=j-1
 return result,sum(cost[i][j] for i,j in enumerate(result))
# All104 rows remain; two genuine18-row stripes create four higher-capacity buckets.
stripes=[17,17,18,17,17,18];buckets=[];r0=0
for h in stripes:
 for x0,x1 in [(0,1160),(1360,2520)]:
  buckets.append(dict(x0=x0,x1=x1,row0=r0,rows=h,center=(2.16+(x0+x1)*.054/2,56.16+(r0+h/2)*.270)))
 r0+=h
assert r0==104
quads=sorted(g for g in groups if g.startswith('quad['));small=sorted(g for g in groups if not g.startswith('quad['))
qassign,qcost=hungarian([[anchorcost(g,b['center']) for b in buckets] for g in quads]);base={j:[g] for g,j in zip(quads,qassign)}
eligible=[i for i,b in enumerate(buckets) if b['rows']==18];best=None
for doubled in itertools.combinations(eligible,3):
 slots=[j for j in range(12) for _ in range(2 if j in doubled else 1)]
 cost=[[anchorcost(g,buckets[j]['center']) if (j not in doubled or g.startswith('slice[')) else 1e30 for j in slots] for g in small]
 assign,score=hungarian(cost)
 if best is None or score<best[0]:best=(score,slots,assign,doubled)
score,slots,assign,doubled=best;allocation={j:list(gs) for j,gs in base.items()}
for g,k in zip(small,assign):allocation[slots[k]].append(g)
assert all(all(g.startswith('slice[') for g in allocation[j] if not g.startswith('quad[')) for j in doubled)
regions={}
for j,b in enumerate(buckets):
 gs=allocation[j];total=sum(areas[g] for g in gs);span=b['x1']-b['x0'];best_order=None
 for order in itertools.permutations(gs):
  widths=[int(span*areas[g]/total) for g in order]
  for k in sorted(range(len(order)),key=lambda k:-(span*areas[order[k]]/total-widths[k]))[:span-sum(widths)]:widths[k]+=1
  x=b['x0'];cost=0;rs={}
  for g,w in zip(order,widths):
   rs[g]=dict(x0=x,x1=x+w,row0=b['row0'],rows=b['rows'],bucket=j)
   cost+=anchorcost(g,(2.16+(x+w/2)*.054,56.16+(b['row0']+b['rows']/2)*.270));x+=w
  if best_order is None or cost<best_order[0]:best_order=(cost,rs)
 regions.update(best_order[1])
for g,r in regions.items():
 r['area_um2']=areas[g];r['capacity_um2']=(r['x1']-r['x0'])*r['rows']*.054*.270;r['ordinary_fill']=areas[g]/r['capacity_um2'];assert r['ordinary_fill']<.55,(g,r)
# Genuine native hyperedges guide within-cohort positions. Boundary anchors retain
# their actual positions and loads; cells remain constrained only in this MODEL.
xy={}
for g,ns in groups.items():
 r=regions[g]
 centers0={n:((cells[byname[n]]['bbox'][0]+cells[byname[n]]['bbox'][2])/2/u,(cells[byname[n]]['bbox'][1]+cells[byname[n]]['bbox'][3])/2/u) for n in ns}
 xs=[v[0] for v in centers0.values()];ys=[v[1] for v in centers0.values()]
 for n,(x,y) in centers0.items():
  fx=(x-min(xs))/max(.001,max(xs)-min(xs));fy=(y-min(ys))/max(.001,max(ys)-min(ys))
  xy[n]=(2.16+(r['x0']+fx*(r['x1']-r['x0']))*.054,56.16+(r['row0']+fy*r['rows'])*.270)
links=collections.defaultdict(list)
for net,ns in nets.items():
 if net not in clocknets:
  for n in ns:links[n].append(net)
portpoints={p['net']:center(p['shapes']) for p in pins['ports'] if p['shapes'] and p['net'] not in clocknets and p['role'] not in ['POWER','GROUND']}
for _ in range(16):
 centers={}
 for net,ns in nets.items():
  ps=[xy[n] for n in ns]
  if net in portpoints:ps.extend([portpoints[net]]*4)
  centers[net]=(sum(x for x,y in ps)/len(ps),sum(y for x,y in ps)/len(ps))
 for n,ids in links.items():
  r=regions[co[n]];x=sum(centers[z][0] for z in ids)/len(ids);y=sum(centers[z][1] for z in ids)/len(ids)
  xy[n]=(max(2.16+r['x0']*.054,min(2.16+r['x1']*.054,.25*xy[n][0]+.75*x)),max(56.16+r['row0']*.270,min(56.16+(r['row0']+r['rows'])*.270,.25*xy[n][1]+.75*y)))
plan={};grid=[bytearray(2520) for _ in range(104)]
for g,ns in groups.items():
 r=regions[g];ns=sorted(ns,key=lambda n:(xy[n][1],n));total=sum(width(n) for n in ns);assigned=[[] for _ in range(r['rows'])];run=0
 for n in ns:
  w=width(n);rr=min(r['rows']-1,int((run+w/2)*r['rows']/total));assigned[rr].append(n);run+=w
 for rr,ns in enumerate(assigned):
  ns.sort(key=lambda n:(xy[n][0],n));free=r['x1']-r['x0']-sum(width(n) for n in ns);assert free>=0,(g,rr,free)
  cursor=r['x0'];previous=0
  for k,n in enumerate(ns):
   gap=free*(k+1)//(len(ns)+1);cursor+=gap-previous;previous=gap;w=width(n);row=r['row0']+rr
   assert not any(grid[row][cursor:cursor+w]);grid[row][cursor:cursor+w]=bytes([1])*w
   oldc=cells[byname[n]];plan[byname[n]]=dict(canonical_cell=n,cohort=g,master=oldc['master'],orient='MX' if str(oldc['orient'])=='MX' else 'R0',location_dbu=[corelo+cursor*site,bandlo+row*rowh],bbox_dbu=[corelo+cursor*site,bandlo+row*rowh,corelo+(cursor+w)*site,bandlo+(row+1)*rowh]);cursor+=w
assert len(plan)==11145
# Row orientation comes from the actual legal row inventory, not cell history.
roworient={round(z[1]):None for z in old['rows']}
for z in cells.values():roworient[z['bbox'][1]]=z['orient']
for c in plan.values():c['orient']=roworient[c['bbox_dbu'][1]];assert c['orient'] in ['R0','MX']
prefix=[array.array('I',[0])*2521]
for row in grid:
 acc=0;line=array.array('I',[0])
 for x,v in enumerate(row):acc+=v;line.append(prefix[-1][x+1]+acc)
 prefix.append(line)
density=[]
for ws,hs in [(50,10),(100,20),(200,40),(100,1)]:
 best=(-1,None)
 for y in range(105-hs):
  a=prefix[y];b=prefix[y+hs]
  for x in range(2521-ws):
   v=b[x+ws]-b[x]-a[x+ws]+a[x]
   if v>best[0]:best=(v,(x,y))
 density.append(dict(window_um=[ws*.054,hs*.270],maximum_fill=best[0]/(ws*hs),origin_um=[2.16+best[1][0]*.054,56.16+best[1][1]*.270],scope='EXACT exhaustive every legal site/row aligned window'))
def pinxy(c,p,modeled):
 if c is None:return center(ports[p]['shapes'])
 pin=contacts[c,p];q=center(pin['shapes'])
 if not modeled:return q
 oc=cells[byname[c]];nc=plan[byname[c]];ob=oc['bbox'];nb=nc['bbox_dbu'];dx=(nb[0]-ob[0])/u
 # A changed row orientation reflects around the cell-height center.
 if oc['orient']==nc['orient']:return (q[0]+dx,q[1]+(nb[1]-ob[1])/u)
 assert set([oc['orient'],nc['orient']])=={'R0','MX'}
 return (q[0]+dx,(nb[1]+nb[3])/2/u-(q[1]-(ob[1]+ob[3])/2/u))
ledger=[];wire_summary={}
for modeled in [False,True]:
 rows=[]
 for net in caps['all_driver_nets']:
  drv=net['driver'];cs=net['contacts']
  if drv['cell'] is None and ports[drv['pin']]['net'] in clocknets:continue
  a=pinxy(drv['cell'],drv['pin'],modeled);points=[pinxy(c['cell'],c['pin'],modeled) for c in cs];allp=[a]+points
  hpwl=max(x for x,y in allp)-min(x for x,y in allp)+max(y for x,y in allp)-min(y for x,y in allp)
  branches=[abs(x-a[0])+abs(y-a[1]) for x,y in points];star=sum(branches);base=net['cap_ff'];limit=net['native_max_cap_ff']
  row=dict(driver=drv,contacts=len(points),hpwl_um=hpwl,unobstructed_star_um=star,max_direct_branch_um=max(branches,default=0),native_plus_external_cap_fF=base,hpwl_wire_cap_model_fF=hpwl*.165790,star_wire_cap_model_fF=star*.165790,hpwl_total_cap_model_fF=base+hpwl*.165790,star_total_cap_model_fF=base+star*.165790,native_max_cap_fF=limit,kind='boundary' if drv['cell'] is None or any(c['cell'] is None for c in cs) else 'internal')
  rows.append(row)
 wire_summary['model' if modeled else 'actual_checkpoint_geometry']=dict(nonclock_driver_nets=len(rows),total_hpwl_um=sum(r['hpwl_um'] for r in rows),total_unobstructed_star_um=sum(r['unobstructed_star_um'] for r in rows),maximum_direct_branch_um=max(r['max_direct_branch_um'] for r in rows),internal_max_direct_branch_um=max(r['max_direct_branch_um'] for r in rows if r['kind']=='internal'),hpwl_cap_over_limit=[r for r in rows if r['native_max_cap_fF'] and r['hpwl_total_cap_model_fF']>r['native_max_cap_fF']],star_cap_over_limit_count=sum(bool(r['native_max_cap_fF'] and r['star_total_cap_model_fF']>r['native_max_cap_fF']) for r in rows))
 if modeled:ledger=rows
metal=json.load(gzip.open(I/'metal.json.gz','rt'));pg=collections.defaultdict(lambda:dict(shapes=0,rectangle_area_sum_um2=0))
for layer,box,role,owner in metal['shapes']:
 key=layer+':'+owner.split(':')[0]+':'+role;pg[key]['shapes']+=1;pg[key]['rectangle_area_sum_um2']+=(box[2]-box[0])*(box[3]-box[1])/u**2
summary=dict(scope='SOURCE MODEL ONLY; original actual70042checkpoint untouched; NO engine/ODB generation/CTS/route',canonical_cells=8265,source_ledger_scalar_port_aliases=port_aliases,cells=11145,ff=2904,added_ff=0,added_edges=0,all_legal_rows=504,allocation_rows=104,cohorts=len(groups),cohort_count={g:len(ns) for g,ns in groups.items()},regions=regions,ordinary_area_um2=sum(areas.values()),band_capacity_um2=3821.1264,ordinary_band_fill=sum(areas.values())/3821.1264,clock_spine=dict(x_um=[64.8,75.6],width_um=10.8,rows=104,area_um2=303.264,source_sink_contacts=2904,source_sink_cap_fF=1378.633344,reference='Actual INT8253clockcells/75.85974um2 at2782sinks; scaling is sensitivity, NOT clock implementation',scaled_reference_area_um2=75.85974*2904/2782,conservative_all_BUFx24_cells=265,conservative_native_area_um2=265*clockcell['area_um2'],conservative_added_clock_input_cap_fF=265*clockcell['input_A_cap_fF'],clockcell=clockcell,conservative_spine_fill=265*1.62*.270/303.264,site_capacity_at6_BUFx24_per_row=624,area_to55percent_after265_BUFx24_um2=3821.1264*.55-sum(areas.values())-265*1.62*.270,actual_tree=None,actual_spread=None),density_windows=density,wire=wire_summary,wire_model=dict(source='Exact native MTerm largest-access-rectangle centers and real BPin centers',signal_R_kohm_per_um=.0265684,signal_C_fF_per_um=.165790,scope='Pin-access-specific HPWL floor and unobstructed rectilinear-star construction; obstacle detours/vias/real tree unknown. Neither is extracted RC or a timing closure.',TT_setup='Source ideal-wire +262.959503ps only; model adds nonzero wire cap but no characterized path replay yet',FF_hold='Unqualified: no actual clock/neighbor phase; no zero-clock or arrival-padding proof'),native_PG=dict(reference_checkpoint_sha256='70042afe82ff76fc2657f45fb6c2a89f91eed2993add8e9dc89f2fc612fc88a6',actual_reference_shapes=len(metal['shapes']),actual_reference_vias=len(metal['vias']),actual_reference_terminal_contacts=22290,geometry_cost=pg,metal_area_scope='Raw rectangle sums, including overlaps; not occupied union or free routing capacity',source_model_only='New site positions require real native PG/contact/short re-audit after a separately granted placement; no current checkpoint mutation'),assignment=dict(method='Actual native graph gives27 independent cohorts; cap-weighted actual-port Hungarian assignment of12quads; all4 choices of3 doubled18row buckets, exact15small-cohort assignment; best within-bucket ordering;16 local native-hyperedge barycentric iterations; legal native-width quantiles and uniform site gaps',double_buckets=list(doubled),cohort_groups=allocation),open=['ROOT model PNG/source review','New exact placement grant','Actual post-placement PG/short/strict/identity proof','Actual signal access/routes/cap/slew/setup','Actual2904sink CTS clockcap/wire/insertion/spread','Real parent boundary and hold repair cost','Whole HIDX reset/storage/ownership/throughput release'])
(O/'MODEL.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(O/'site_plan.json.gz','wt') as f:json.dump(plan,f,separators=(',',':'))
with gzip.open(O/'all_native_wire_cap_ledger.json.gz','wt') as f:json.dump(ledger,f,separators=(',',':'))
print(json.dumps({k:summary[k] for k in ['cells','cohorts','ordinary_area_um2','density_windows']}));print(json.dumps(wire_summary))

import json,gzip,math,array,itertools,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
source=(P/'kit/joint_model.py').read_text();ns={'__file__':str(P/'kit/joint_model.py')}
exec(compile(source.split('plan={};grid=')[0].replace("O=P/'out'","O=P/'final_defs'"),str(P/'kit/joint_model.py'),'exec'),ns)
D=json.load(open(P/'DEMANDS.json'));items=json.load(open(P/'ACTUAL_ITEMS.json'));byitem={i['id']:i for i in items};allocation=ns['allocation'];buckets=ns['buckets'];areas=ns['areas'];anchorcost=ns['anchorcost'];changes=[]
def width(g,j):return D[str(buckets[j]['rows'])][g]['width_sites']
def demand(j):return sum(width(g,j) for g in allocation[j])
# Correct actual-demand overflow by least native-port-weighted reassignment.
while any(demand(j)>1160 for j in allocation):
 candidates=[]
 for j in allocation:
  if demand(j)<=1160:continue
  for g in allocation[j]:
   for k in allocation:
    if k==j or demand(k)+width(g,k)>1160:continue
    # Leave enough native mass for the genuine 40–60% regional contract.
    a=sum(areas[z] for z in allocation[j] if z!=g)
    if a/(1160*buckets[j]['rows']*.054*.270)<.40:continue
    cost=anchorcost(g,buckets[k]['center'])-anchorcost(g,buckets[j]['center'])
    candidates.append((cost,g,j,k))
 if not candidates:raise RuntimeError(('DEMAND_CAPACITY_CONTRADICTION',{j:demand(j) for j in allocation}))
 cost,g,j,k=min(candidates);allocation[j].remove(g);allocation[k].append(g);changes.append({'cohort':g,'from':j,'to':k,'native_port_cost_delta':cost})
regions={};plan={};u=ns['u'];site=ns['site'];rowh=ns['rowh'];byname=ns['byname'];cells=ns['cells'];co=ns['co'];roworient={z['bbox'][1]:z['orient'] for z in cells.values()};grid=[bytearray(2520) for _ in range(104)]
for j,gs in allocation.items():
 b=buckets[j];H=b['rows'];W={g:width(g,j) for g in gs};slack=1160-sum(W.values())
 # Distributed real empty sites; never filler or fictitious capacitance.
 for _ in range(slack):
  feasible=[g for g in gs if areas[g]/((W[g]+1)*H*.054*.270)>=.40]
  assert feasible,('NATIVE_MASS_BELOW40',j)
  g=max(feasible,key=lambda g:(areas[g]/(W[g]*H*.054*.270),g));W[g]+=1
 best=None
 for order in itertools.permutations(gs):
  x=b['x0'];cost=0
  for g in order:cost+=anchorcost(g,(2.16+(x+W[g]/2)*.054,56.16+(b['row0']+H/2)*.270));x+=W[g]
  if best is None or cost<best[0]:best=(cost,order)
 x=b['x0']
 for g in best[1]:
  z=D[str(H)][g];ratio=W[g]/z['width_sites'];r=dict(x0=x,x1=x+W[g],row0=b['row0'],rows=H,bucket=j,area_um2=areas[g],capacity_um2=W[g]*H*.054*.270,ordinary_fill=areas[g]/(W[g]*H*.054*.270),minimum_constructed_width_sites=z['width_sites'],actual_atom_reservations=z['reserved_atom_sites'],side_routing_reserve_sites=16);regions[g]=r
  assert .40<=r['ordinary_fill']<=.60
  for pp in z['placements']:
   it=byitem[pp['id']];xx=x+math.floor(pp['xsite']*ratio);yy=b['row0']+pp['row']
   for n,dx,dy in it['members']:
    oc=cells[byname[n]];w=(oc['bbox'][2]-oc['bbox'][0])//site;cx=xx+dx;cy=yy+dy
    assert cx+w<=r['x1'] and cy<r['row0']+H and not any(grid[cy][cx:cx+w]),('CELL_OVERLAP',n)
    grid[cy][cx:cx+w]=bytes([1])*w
    bbox=[ns['corelo']+cx*site,ns['bandlo']+cy*rowh,ns['corelo']+(cx+w)*site,ns['bandlo']+(cy+1)*rowh]
    plan[byname[n]]=dict(canonical_cell=n,cohort=g,master=oc['master'],orient=roworient[bbox[1]],location_dbu=bbox[:2],bbox_dbu=bbox)
  x+=W[g]
assert len(plan)==11145 and len({c['canonical_cell'] for c in plan.values()})==11145
prefix=[array.array('I',[0])*2521]
for row in grid:
 acc=0;line=array.array('I',[0])
 for x,v in enumerate(row):acc+=v;line.append(prefix[-1][x+1]+acc)
 prefix.append(line)
density=[]
for ws,hs in [(50,10),(100,20),(200,40),(100,1)]:
 best=(-1,None)
 for y in range(105-hs):
  a=prefix[y];bb=prefix[y+hs]
  for x in range(2521-ws):
   v=bb[x+ws]-bb[x]-a[x+ws]+a[x]
   if v>best[0]:best=(v,(x,y))
 density.append(dict(window_um=[ws*.054,hs*.270],maximum_fill=best[0]/(ws*hs),origin_um=[2.16+best[1][0]*.054,56.16+best[1][1]*.270]))
O=P/'out_demand';O.mkdir()
with gzip.open(O/'site_plan.json.gz','wt') as f:json.dump(plan,f,separators=(',',':'))
model=dict(scope='SOURCE_ONLY_DEMAND_PACKING_NOT_IMPLEMENTATION',cells=11145,ff=2904,regions=regions,density_windows=density,allocation=allocation,demand_driven_reassignments=changes,clock_spine_um=[64.8,75.6],new_drive_buffers=0,lower_bound_note='Native area /60%, atom area /rowcount and widest atom are necessary bounds; stored width is a verified finite constructive packing, not a proof of global minimum.',routing_cost='Every functional atom carries real native widths and explicit free sites; 8-site margins on each region side are physical candidates only. Complete native ownership/PG/defaultvia/RC/clock obligations remain OPEN until constructor.',source_sha256=hashlib.sha256(source.encode()).hexdigest())
(O/'MODEL.json').write_text(json.dumps(model,indent=2));print(json.dumps({'status':'COMPLETE_NATIVE_CELL_SOURCE_COORDINATES_ONLY','changes':changes,'density_windows':density}))

"""Finite SOURCE MODEL, no RTL/netlist/ODB or EDA. Native LEF pin-center proxy.
One source-owned 3-row atom per actual driver; one shared wire tree per source.
"""
import json,gzip,pathlib,re,sys,math,collections,hashlib
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
P=pathlib.Path(__file__).parent;K=P/'kit';sys.path.insert(0,str(K))
from dft.liberty import read_liberty
from lib_native import blocks,scalar
load=lambda n:json.load(gzip.open(K/'inputs'/(n+'.json.gz'),'rt'))
R=load('raw');B=load('positions');A=json.load(open(K/'allowlist.json'));M=next(iter(R['modules'].values()))
old=json.load(open(P/'previous_refusal.json'));G=old['source_group_inventory']['all_groups']
L={c:read_liberty(sorted((K/'inputs/native_libs').glob('*'+c+'*'))) for c in ('TT','FF')}
clock={r['instance']:r for r in json.load(open(K/'inputs/clock_cost.json'))['rows']}
removed={n for n,r in clock.items() if not r['open_output_clock_load']}
masters={n:c['type'] for n,c in M['cells'].items() if n not in removed}
masters.update({n:r['new_master'] for n,r in A['replacement_cells'].items()})
masters.update({n:r['master'] for n,r in A['added_cells'].items()})
newclock={f'MODEL_clock_l{lev}_{i}':'BUFx24_ASAP7_75t_R' for lev,count in [(0,1),(1,16),(2,128)] for i in range(count)};masters.update(newclock)
# Parse actual native LEF rectangles, retaining complete source shape geometry.
# These transformed master shapes are not a native ODB/export or routed access certificate.
lef={};text=(P/'input/cells.lef').read_text()
for z in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1\s*$',text,re.M|re.S):
 body=z[2];size=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body);pins={}
 for q in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\s*$',body,re.M|re.S):
  shapes=[];layer=None
  for line in q[2].splitlines():
   if 'LAYER ' in line:layer=line.split()[1]
   if 'RECT ' in line:shapes.append([layer,list(map(float,line.split()[1:5]))])
  pins[q[1]]=shapes
 lef[z[1]]=dict(w=float(size[1]),h=float(size[2]),pins=pins)
assert all(m in lef for m in masters.values())
width={m:round(lef[m]['w']/.054) for m in set(masters.values())}
def relpin(n,p):
 shapes=lef[masters[n]]['pins'][p];assert shapes,(n,p)
 layer,b=max(shapes,key=lambda q:((q[1][2]-q[1][0])*(q[1][3]-q[1][1]),q))
 return ((b[0]+b[2])/2,(b[1]+b[3])/2)
netid={r['name']:int(k) for k,r in M['net_metadata'].items()};drivers=collections.defaultdict(list)
for n,c in M['cells'].items():
 for p,bb in c['connections'].items():
  if c['port_directions'][p]=='output':
   for b in bb:drivers[b].append((n,p))
anchors={n:((v['bbox'][0]+v['bbox'][2])/2000,(v['bbox'][1]+v['bbox'][3])/2000) for n,v in B['insts'].items()}
for br in A['branches']:
 q=[anchors[s['cell']] for s in br['sinks']];xy=(sum(a for a,b in q)/len(q),sum(b for a,b in q)/len(q))
 for n in br['buffers'][1:]:anchors[n]=xy
 if br.get('inverter') and br['inverter'] not in anchors:anchors[br['inverter']]=xy
items=[];claimed=set();group_by_driver={}
for g in G:
 ds=drivers[netid[g['source_net']]];assert len(ds)==1;d,p=ds[0];assert d not in group_by_driver
 group_by_driver[d]=g
 hbs=[b['first_HB'] for b in g['branches']];assert len(hbs)==g['total_first_HB_inputs']
 # Native first-HB inputs are split over the rows immediately above/below the
 # driver. Center their real input-pin span on the native driver output pin.
 dp=relpin(d,p);members=[(d,0,1)];minx=0;maxx=width[masters[d]]
 for side in (0,2):
  ns=hbs[side//2::2]
  if not ns:continue
  tw=sum(width[masters[h]] for h in ns)
  firstpin=relpin(ns[0],'A')[0]/.054;lastpin=tw-width[masters[ns[-1]]]+relpin(ns[-1],'A')[0]/.054
  x=round(dp[0]/.054-(firstpin+lastpin)/2)
  for h in ns:members.append((h,x,side));minx=min(minx,x);maxx=max(maxx,x+width[masters[h]]);x+=width[masters[h]]
 members=[(n,x-minx,y) for n,x,y in members]
 assert not claimed.intersection(n for n,x,y in members);claimed.update(n for n,x,y in members)
 items.append(dict(id=g['source_net'],driver=[d,p],members=members,w=maxx-minx,h=3,anchor=anchors[d]))
for n in masters:
 if n not in claimed:items.append(dict(id=n,members=[(n,0,0)],w=width[masters[n]],h=1,anchor=anchors.get(n,(118.8,64.8))))
assert len(claimed)==544+616
# Exactly one finite source-affinity packing. Native widths/sites, 68 retained
# rows, 16 full-band cohorts. No legalizer, native row-phase or access claim.
items.sort(key=lambda a:(a['anchor'][0],a['anchor'][1],a['id']))
total=sum(i['w']*i['h'] for i in items);co=[[] for _ in range(16)];acc=0
for i in items:
 ci=min(15,int(16*(acc+i['w']*i['h']/2)/total));co[ci].append(i);acc+=i['w']*i['h']
plan={};packing=[];X0=10.8;Y0=55.62
for ci,its in enumerate(co):
 occupied=[0]*68;its.sort(key=lambda a:(-a['h'],-a['w'],a['anchor'][1],a['id']))
 for a in its:
  candidates=[]
  for y in range(69-a['h']):
   x=max(occupied[y:y+a['h']]);score=(x+a['w'],abs((Y0+.27*(y+a['h']/2))-a['anchor'][1]),y)
   if x+a['w']<=248:candidates.append((score,x,y))
  assert candidates,('FINITE_ATOM_PACKING_REFUSAL',ci,a['id'])
  _,x,y=min(candidates)
  for rr in range(y,y+a['h']):occupied[rr]=x+a['w']+1
  for n,dx,dy in a['members']:
   xx=X0+ci*13.5+(x+dx)*.054;yy=Y0+(y+dy)*.27
   # R0/MX alternation follows existing row phase source inference, not native placement.
   ri=round((yy-2.16)/.27);orient='R0' if ri%2==0 else 'MX'
   plan[n]=dict(master=masters[n],bbox=[xx,yy,xx+lef[masters[n]]['w'],yy+.27],orient=orient,cohort=ci)
 packing.append(dict(cohort=ci,max_width_sites=max(occupied),rows=68))
assert len(plan)==12491
def point(n,p):
 x,y=relpin(n,p);b=plan[n]['bbox'];return b[0]+x,b[1]+(y if plan[n]['orient']=='R0' else .27-y)
def rmst(points):
 seen={0};edges=[]
 while len(seen)<len(points):
  dist,a,b=min((abs(points[a][0]-points[b][0])+abs(points[a][1]-points[b][1]),a,b) for a in seen for b in range(len(points)) if b not in seen)
  seen.add(b);edges.append((a,b,dist))
 return edges
# Source load is all ACTUAL graph contacts after the immutable exact allowlist,
# not a per-branch allowance. Existing other sinks remain in the shared tree.
connections={n:{p:list(bb) for p,bb in c['connections'].items()} for n,c in M['cells'].items() if n not in removed}
nextid=max(netid.values())+1
for name in A['added_nets']:netid[name]=nextid;nextid+=1
for n in A['added_cells']:connections[n]={}
for r in A['rewired_pins']:connections[r['cell']][r['pin']]=[netid[r['new_net']]]
contacts=collections.defaultdict(list)
for n,pins in connections.items():
 for p,bb in pins.items():
  if p in ('VDD','VSS','CLK'):continue
  direction=M['cells'][n]['port_directions'][p] if n in M['cells'] else ('input' if p=='A' else 'output')
  for bit in bb:contacts[bit].append(dict(cell=n,pin=p,direction=direction))
native={}
for corner in ('TT','FF'):
 nc={}
 for path in sorted((K/'inputs/native_libs').glob('*'+corner+'*')):
  txt=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
  for m,body in blocks(txt,'cell'):
   nc[m]={p:dict(cap=scalar(pb,'capacitance'),rise=scalar(pb,'rise_capacitance'),fall=scalar(pb,'fall_capacitance'),maxcap=scalar(pb,'max_capacitance')) for p,pb in blocks(body,'pin')}
 native[corner]=nc
def pincap(corner,n,p):
 q=native[corner][masters[n]][p];v=[q[k] for k in ('cap','rise','fall') if q[k] is not None];assert v,(corner,n,p);return [min(v),max(v)]
rows=[];small=[]
for a in [i for i in items if 'driver' in i]:
 d,p=a['driver'];cs=contacts[netid[a['id']]];sinks=[r for r in cs if r['direction']=='input']
 ps=[point(d,p)]+[point(r['cell'],r['pin']) for r in sinks];edges=rmst(ps)
 length=sum(e[2] for e in edges);hblist=[g['first_HB'] for g in group_by_driver[d]['branches']]
 hp=[point(d,p)]+[point(n,'A') for n in hblist];hlen=sum(e[2] for e in rmst(hp))
 cornerloads={}
 for c in ('TT','FF'):
  cp=[pincap(c,r['cell'],r['pin']) for r in sinks];base=[sum(v[k] for v in cp) for k in (0,1)]
  cornerloads[c]=dict(pin_cap_fF=base,nominal_whole_source_wire_fF=length*.165790,total_model_fF=[v+length*.165790 for v in base],native_max_cap_fF=native[c][masters[d]][p]['maxcap'])
 rows.append(dict(source_net=a['id'],driver=dict(cell=d,pin=p,master=masters[d]),branch_count=len(hblist),all_actual_new_sinks=sinks,source_access_point_um=ps[0],first_HB_native_pin_points_um=hp[1:],first_HB_tree_length_um=hlen,first_HB_only_nominal_wire_fF=hlen*.165790,whole_source_tree_length_um=length,whole_source_nominal_wire_fF=length*.165790,old_total_0p5_budget_model_refused=length*.165790>.5,corner_loads=cornerloads))
# Full branch legs separately retained, including genuine reset-split fourth HB/inverter.
legs=[]
for br in A['branches']:
 ns=br['buffers'];paths=[]
 for n,k in zip(ns,ns[1:]):paths.append((n,'Y',k,'A'))
 tail=ns[-1]
 if br.get('inverter'):paths.append((tail,'Y',br['inverter'],'A'));tail=br['inverter']
 for s in br['sinks']:paths.append((tail,'Y',s['cell'],s['pin']))
 rs=[]
 for n,p,k,q in paths:
  x,y=point(n,p);X,Y=point(k,q);dist=abs(X-x)+abs(Y-y);rs.append(dict(source=[n,p],sink=[k,q],Manhattan_native_pin_um=dist,nominal_signal_wire_fF=dist*.165790))
 legs.append(dict(source_net=br['source_net'],role=br['role'],first_HB=ns[0],legs=rs))
# Full signal cut demand, actual transformed LEF points plus fixed native BTerms.
netpoints={bit:[point(r['cell'],r['pin']) for r in cs] for bit,cs in contacts.items()}
for name,port in M['ports'].items():
 if name in ('clk','VDD','VSS'):continue
 xy=[((b[1]+b[3])/2000,(b[2]+b[4])/2000) for q in B['bterms'].get(name,[]) for b in q['boxes']]
 for bit in port['bits']:netpoints.setdefault(bit,[]).extend(xy)
cuts=[]
for i in range(1,16):
 x=X0+i*13.5;cross=sum(bool(ps) and min(p[0] for p in ps)<x<max(p[0] for p in ps) for ps in netpoints.values());cuts.append(dict(x_um=x,actual_signal_net_demand=cross))
leaves=[[] for _ in range(128)]
ffs=[n for n,m in masters.items() if L['TT'][m]['ff']];openloads=[n for n,r in clock.items() if r['open_output_clock_load']]
for i,n in enumerate(sorted(ffs+openloads,key=lambda n:plan[n]['bbox'])):leaves[min(127,i*128//2892)].append(n)
clockrows=[]
for i,ns in enumerate(leaves):
 root=f'MODEL_clock_l2_{i}';ps=[point(root,'Y')];caps={c:0 for c in ('TT','FF')}
 for n in ns:
  p=next(p for p,z in L['TT'][masters[n]]['pins'].items() if z['clock']) if n in ffs else 'A';ps.append(point(n,p))
  for c in caps:caps[c]+=pincap(c,n,p)[1]
 edges=rmst(ps);length=sum(e[2] for e in edges)
 clockrows.append(dict(leaf=root,sinks=len(ns),RMST_um=length,native_pin_cap_fF=caps,nominal_clock_wire_fF=length*.145426))
pg=json.load(open(P/'old_pg_projection.json'));oldclear=sum(pg['summary'][f'{l}:via_landing:all']['pg_clear'] for l in ('M2','M4'))
area=sum(L['TT'][m]['area'] for m in masters.values());maxcut=max(r['actual_signal_net_demand'] for r in cuts)
result=dict(schema='int8.source_owned_atoms.model.v1',status='REFUSED_FOR_BUILD_WHOLE_PATH_AND_JOINT_ROUTING_UNQUALIFIED',source_groups=544,branches=616,D_branches=594,RESETN_branches=10,reset_split_branches=12,
 all_cells=len(plan),FF=len(ffs),native_area_um2=area,PG_terminals=2*len(plan),band_um=[10.8,55.62,216,18.36],band_fill=area/(216*18.36),whole_outline_fill=area/(237.6*129.6),all464rows_retained=True,
 source_atoms=dict(rows=3,all544source_firstHB_atoms=True,firstHB_owned_cells=616,total_source_tree_budget=True,max_firstHB_tree_um=max(r['first_HB_tree_length_um'] for r in rows),max_firstHB_nominal_wire_fF=max(r['first_HB_only_nominal_wire_fF'] for r in rows),max_whole_source_nominal_wire_fF=max(r['whole_source_nominal_wire_fF'] for r in rows),old0p5_total_budget_refusals=sum(r['old_total_0p5_budget_model_refused'] for r in rows),old0p5_firstHB_only_refusals=sum(r['first_HB_only_nominal_wire_fF']>.5 for r in rows)),
 downstream=dict(max_native_pin_Manhattan_um=max(z['Manhattan_native_pin_um'] for r in legs for z in r['legs']),all_branch_legs=len(legs),wire_RC='nominal signal model only; actual layers/vias/extraction remain NULL'),
 cuts=cuts,capacity=dict(old_PG_projected_M2_M4_clear_rays=oldclear,signal_peak=maxcut,remaining_before_clock_newPG_vias=oldclear-maxcut,canonical_PG_method_commit='5b100ce330bd619261dfdf087e5a2df3bc6fff7d',fresh_PG_contact_deduction=None,clock_track_deduction=None,joint_track_assignment=None,verdict='REFUSE no independent subtraction or free residual asserted'),
 fresh_clock=dict(levels=[1,16,128],functional_buffers=145,retained_genuine_open_loads=110,real_sinks=2892,max_leaf_sinks=max(map(len,leaves)),all_clock_area_um2=76.73454,clock_leaf_models=clockrows,early_late_arrivals=None,TT_FF_spread=None,pulse_domain=None,phase='old253 phases discarded'),
 whole_path_budget=dict(old34p62293_headroom_discarded=True,old_source_input_slew_not_transferred=True,fresh_native_driver_waveforms=None,source_HB_D_RESETN_whole_path_minmax=None,SS_setup=None,FF_hold=None,seven_feedback_conditions='OPEN',TT292lower_wire_predicates='OPEN; nominal model is not minimum actual wire',native_CQ_domain='OPEN'),
 actual_physical_capacitance=None,actual_pin_via_access=None,source_implementation=False,EDA=False,placement_grant=False,full_token_rate=None)
(P/'model.json').write_text(json.dumps(result,indent=2)+'\n');(P/'source_atoms.json').write_text(json.dumps(rows,indent=2)+'\n');(P/'branch_legs.json').write_text(json.dumps(legs,indent=2)+'\n')
with gzip.open(P/'site_plan.json.gz','wt') as f:json.dump(plan,f)
fig,ax=plt.subplots(figsize=(15,9));groups=collections.defaultdict(list)
for n,v in plan.items():
 b=v['bbox'];kind='source-owned atom' if n in claimed else 'clock' if n in newclock or n in clock else 'sink-owned remaining HB' if n in A['added_cells'] else 'native state/signal'
 groups[kind].append(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1]))
colors={'source-owned atom':'#c17525','clock':'#a243ac','sink-owned remaining HB':'#21976a','native state/signal':'#4286b6'}
for k,rs in groups.items():ax.add_collection(PatchCollection(rs,facecolor=colors[k],edgecolor='none',label=k))
for y,h in [(2.16,53.46),(73.98,53.46)]:ax.add_patch(Rectangle((2.16,y),233.28,h,facecolor='#d5e5eb',alpha=.4))
for ps in B['bterms'].values():
 for q in ps:
  for b in q['boxes']:ax.add_patch(Rectangle((b[1]/1000,b[2]/1000),max(.1,(b[3]-b[1])/1000),max(.1,(b[4]-b[2])/1000),color='#222'))
ax.text(118.8,108,f'544 native driver/first-HB atoms; all 616 first branches source-owned\n{result["source_atoms"]["old0p5_total_budget_refusals"]} shared-source trees exceed nominal 0.5 fF; complete path budget REFUSED',ha='center')
ax.text(118.8,20,f'{maxcut} crossing signal nets; {oldclear} OLD-PG-clear rays\nJoint fresh clock/new PG/via/RC allocation unresolved; no capacity PASS',ha='center')
ax.set(xlim=(0,237.6),ylim=(0,129.6),aspect='equal',xlabel='um',ylabel='um',title='INT8 source-owned native-pin atom MODEL — BUILD REFUSED\n12,491 cells; 1,668.41856 um²; all 2,782 FF / 604 endpoints retained; no engine')
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],marker='s',linestyle='',color=colors[k],label=f'{k}: {len(v)}') for k,v in groups.items()],fontsize=8,loc='upper right')
fig.text(.08,.025,'One finite source packing. LEF pin-center wire is a nominal model, never extracted RC or minimum-load proof. IO80fF and all full-face pins retained.\nFresh clock, SS/FF whole-path timing, PG birth/contact/conductor/shorts, native site/phase/access and complete transparent all-driver census remain OPEN.',fontsize=9)
fig.tight_layout(rect=[0,.065,1,1]);fig.savefig(P/'MODEL.png',dpi=180)
print(json.dumps({k:result[k] for k in ['status','source_atoms','downstream','capacity']},indent=2))

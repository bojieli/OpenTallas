import json,gzip,math,re,collections,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=pathlib.Path(__file__).resolve().parent.parent;O=B/'overlay';T=json.load(open(O/'type_overlay.json'));Q=json.load(gzip.open(B/'private_proposal_v2.json.gz'));G=json.load(gzip.open(B/'native_graph_r5.json.gz'));SM=json.load(gzip.open(O/'semantic_window_membership.json.gz'));MA=json.load(gzip.open(O/'native_local_FF_masters.json.gz'));C=json.load(gzip.open(O/'canonical_pack_5.95.json.gz'));W,H=T['outline_um'];bands=Q['landing_bands_entire_cell_bbox_um'];ft={x['name']:x for x in T['ft_slots']}
def center(r):return [(r[0]+r[2])/2,(r[1]+r[3])/2]
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-8 and min(a[3],b[3])>max(a[1],b[1])+1e-8
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def nat(n):return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)',n)]
def area_cells(ns):return sum(math.prod(G['native_DFF_bboxes_um'][MA[n]['master']]) for n in ns)
def portpoint(name):
 z=C['windows'].get(name)
 if not z:return None
 f=z['face'];q=z['center'];return [q if f in 'NS' else(12.96 if f=='W' else W-12.96),q if f in 'EW' else(12.96 if f=='S' else H-12.96)]
# Stream priors are actual primary/publication supports; unanchored arithmetic banks use exact sequential graph.
banks=G['stream_native_bank_counts'];adj=collections.defaultdict(collections.Counter);priors={}
for a,ss in G['stream_native_bank_dependencies'].items():
 for b,n in ss.items():adj[a][b]+=n;adj[b][a]+=n
for a in banks:
 rows=[(portpoint(p),n) for k in ['stream_native_primary_input_support','stream_native_publication_support'] for p,n in G[k].get(a,{}).items() if portpoint(p)]
 if rows:priors[a]=[sum(p[k]*n for p,n in rows)/sum(n for p,n in rows) for k in (0,1)]
pos={a:priors.get(a,[W/2,H/2]) for a in banks}
for _ in range(80):pos={a:priors.get(a,[sum(pos[b][k]*n for b,n in adj[a].items())/sum(adj[a].values()) for k in (0,1)] if adj[a] else pos[a]) for a in banks}
reset=T['clock']['landing_contract']['collector_tree'];rp={z['name']:z['xy'] for z in reset['relays']};rq={z['q']:z['xy'] for z in reset['relays']};cp={z['name']:z['xy_um'] for z in T['clock']['landing_contract']['pins']};unresolved=[];groups=[]
for x in SM['groups']:
 if not x['group'].startswith('UNRESOLVED_'):continue
 ns=x['native_named_FFs'];n=ns[0];role=None;p=None;ev=None;kind=None
 m=re.match(r'u_bound\.u_ft_(.+)_o_(\d+)\.',n)
 if m:
  role='actual FT stage';kind='FT';p=ft[m[1]]['regs_um'][int(m[2])];ev={'slot':m[1],'stage':int(m[2]),'frozen_stations':ft[m[1]]['stations']}
 elif '.u_stream.' in n:
  bank=re.sub(r'\[\d+\]','[*]',n.split('u_stream.',1)[1].split('$_')[0]);p=pos[bank];role='actual native stream register bank (arithmetic role not inferred)';kind='stream';ev={'bank':bank,'direct_IO_support':{'inputs':G['stream_native_primary_input_support'].get(bank,{}),'outputs':G['stream_native_publication_support'].get(bank,{})},'native_neighbor_banks':G['stream_native_bank_dependencies'].get(bank,{})}
 elif n.startswith(('u_bound.u_bin_','u_bound.u_bout_')):
  bn=n.split('.')[1].split('_',2)[2];p=portpoint(bn);role='actual named native boundary register bank';kind='boundary';ev={'bus':bn,'port':C['windows'].get(bn)}
 elif '.u_tload.' in n:p=[25.92,427.68];role='actual loader control (NOT ROM data-firstcapture)';kind='tload';ev={'native_modules':sorted({z.split('$_')[0].split('[')[0] for z in ns})}
 else:
  mod=n.split('.')[1];kind='control';role='actual reset/start/collector vertex'
  if mod in rp:p=rp[mod];ev={'reset_relay':mod,'fixed_same_topology_point':p}
  elif mod.startswith('u_srl_') and mod.replace('u_srl_','u_rrl_') in rp:p=rp[mod.replace('u_srl_','u_rrl_')];ev={'start_same_source_reset_relay_site':mod.replace('u_srl_','u_rrl_'),'vertex':mod}
  elif mod=='u_rst_in':p=T['reset']['tap_um'];ev={'reset_entry':True}
  elif mod=='u_run_in':p=next(([z['x'],z['y']] for z in json.load(gzip.open(O/'named_pin_locations.json.gz')) if z['name']=='start_i'),None);ev={'start_entry':True}
  elif mod=='u_cland_rstart_tx':p=cp.get('cland_rstart_out');ev={'native_collector_start_export':'cland_rstart_out'}
  elif mod=='u_cland_origin':p=cp.get('cland_tstart_in');ev={'native_origin':True}
  elif mod.startswith('u_cland_fstart_'):p=cp.get('cland_fstart_out_'+mod[len('u_cland_fstart_'):]);ev={'native_forwarded_start_export':mod}
  elif mod.startswith('u_cland_rst_') and mod[len('u_cland_rst_'):] in bands:p=center(bands[mod[len('u_cland_rst_'):]]);ev={'native_ring_reset':mod[len('u_cland_rst_'):]}
  elif mod.startswith(('u_cland_collect_','u_cland_reset_')):
   net=re.sub(r'^u_cland_(collect|reset)_','',mod);p=rq.get(net,reset['root'] if net in ('rst_root_n','rst_root') else None);ev={'native_existing_reset_net':net}
  elif n.startswith('u_bound.u_core.u_rl.'):p=center(Q['core_publication_relay_box']);ev={'native_core_reset_synchronizer':True}
 if p is None:unresolved.append({'group':x['group'],'native_named_FFs':ns,'reason':'native role known but exact declared control/consumer point unresolved; NO fallback whole-outline average'});continue
 # Physical packing tiles use at most512 real FFs, unrelated to tap IDs/capacity. Each tile is contiguous natural native-name order.
 ns=sorted(ns,key=nat)
 for i in range(0,len(ns),512):
  sub=ns[i:i+512];groups.append({'group':x['group'],'tile':i//512,'native_named_FFs':sub,'count':len(sub),'area_um2':area_cells(sub),'kind':kind,'role':role,'actual_connectivity':ev,'desired_point':p})
# Coalesce exact same native vertex points into ONE finite window, preserving exact member identities.
ctrl=collections.defaultdict(list);rest=[]
for z in groups:
 if z['kind']=='control':ctrl[tuple(z['desired_point'])].append(z)
 else:rest.append(z)
for p,zz in ctrl.items():
 ns=[n for z in zz for n in z['native_named_FFs']];rest.append(dict(group='control_site_'+str(p),tile=0,native_named_FFs=ns,count=len(ns),area_um2=area_cells(ns),kind='control',role='actual fixed native control vertices sharing source point',actual_connectivity=[z['actual_connectivity'] for z in zz],original_groups=[z['group'] for z in zz],desired_point=list(p)))
groups=rest
# Finite regions are NEW private intent. Existing macro halos/18 semantic windows retained.
block=[z['existing_whole_cell_window_um'] for z in SM['groups'] if z['existing_whole_cell_window_um']]
for h in T['hard_cores']:
 x,y=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);block.append([x+dx-4.32,y+dy-4.32,x+dx+121.848+4.32,y+dy+62.952+4.32])
placed=[];fails=[]
# Larger actual banks first; legal finite rectangles from4.32um lattice, no clock target included in objective.
for z in sorted(groups,key=lambda z:(z['kind']!='control',-z['area_um2'],z['group'],z['tile'])):
 if z['kind']=='control':
  # Existing control points fixed: finite physical master-fit box, explicit overlap census below.
  width=4.32;height=max(.54,math.ceil(z['area_um2']/.5/width/.27)*.27);x,y=z['desired_point'];r=[max(4.32,min(W-4.32-width,x-width/2)),max(4.32,min(H-4.32-height,y-height/2)),0,0];r[2]=r[0]+width;r[3]=r[1]+height;z['window_um']=r;z['occupancy']=z['area_um2']/(width*height);z['fixed_vertex_window']=True;placed.append(z);block.append(r);continue
 need=z['area_um2']/.5;shapes=[]
 for w in [12.96,17.28,21.6,25.92,30.24,34.56,43.2]:
  h=math.ceil(need/w/4.32)*4.32
  if max(w/h,h/w)<=3 and h>=4.32:shapes.append((w,h))
 best=None
 for w,h in shapes:
  for ix in range(1,math.floor((W-4.32-w)/4.32)+1):
   x=ix*4.32
   for iy in range(1,math.floor((H-4.32-h)/4.32)+1):
    y=iy*4.32;r=[x,y,x+w,y+h];d=dist(center(r),z['desired_point'])
    if d>110:continue
    if any(overlap(r,b) for b in block):continue
    score=d+(w*h-need)*.005
    if best is None or score<best[0]:best=(score,r)
 if best is None:fails.append(z);continue
 z['window_um']=best[1];z['relocation_L1_um']=dist(center(best[1]),z['desired_point']);z['occupancy']=z['area_um2']/((best[1][2]-best[1][0])*(best[1][3]-best[1][1]));placed.append(z);block.append(best[1])
# Explicit soft control overlaps are recorded, never concealed as collision-free actual placement.
controls=[z for z in placed if z['kind']=='control'];bank=[z for z in placed if z['kind']!='control'];ov=[]
for z in controls:
 hits=[a['group']+':'+str(a['tile']) for a in bank if overlap(z['window_um'],a['window_um'])];macro=[]
 for h in T['hard_cores']:
  x,y=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);r=[x-4.32,y+dy-4.32,x+121.848+4.32,y+dy+62.952+4.32]
  if overlap(z['window_um'],r):macro.append(h['inst'])
 if hits or macro:ov.append({'control':z['group'],'bank_overlap':hits,'macro_halo_overlap':macro})
for z in placed:
 r=z['window_um'];mw=max(G['native_DFF_bboxes_um'][MA[n]['master']][0] for n in z['native_named_FFs']);z['conservative_row_slots']=math.floor((r[2]-r[0]+1e-8)/mw)*math.floor((r[3]-r[1]+1e-8)/.27);z['actual_FF_row_fit']=z['conservative_row_slots']>=z['count'];z['row_height_um']=.27;z['site_width_um']=.054;z['maximum_actual_master_width_um']=mw
control_pairs=[dict(a=a['group'],b=b['group']) for i,a in enumerate(controls) for b in controls[i+1:] if overlap(a['window_um'],b['window_um'])]
allffarea=sum(n*math.prod(G['native_DFF_bboxes_um'][k]) for k,n in G['native_leaf_counts'].items() if k in G['native_DFF_bboxes_um'])
summary={'all68857_DFF_actual_LEF_area_um2':allffarea,'actual_nonFF_standard_cell_area_um2':30846.92058-allffarea,'nonFF_regional_placement':'UNRESERVED/UNQUALIFIED:10691.5869um2 mapped standard combinational area still requires whole-logic placement; FF-only geometry is not regional logic-capacity PASS','control_control_overlaps':len(control_pairs),'failed_conservative_row_fits':sum(not z['actual_FF_row_fit'] for z in placed),'local_occupancy_proposal':.50,'scope':'NEW private finite placement intent ONLY; no GEN/CAD/source/endpoint/clock identity changes','native_unresolved_input':38821,'new_window_FFs':sum(z['count'] for z in placed),'unallocated_FFs':sum(z['count'] for z in fails)+sum(len(z['native_named_FFs']) for z in unresolved),'new_regions':len(placed),'unplaced_tiles':len(fails),'unresolved_control_roles':len(unresolved),'explicit_control_overlaps':len(ov),'total_new_exact_FF_master_area_um2':sum(z['area_um2'] for z in groups),'bank_window_area_um2':sum((z['window_um'][2]-z['window_um'][0])*(z['window_um'][3]-z['window_um'][1]) for z in bank),'max_bank_occupancy':max((z['occupancy'] for z in bank),default=0),'endpoints_unchanged':76,'no_clock_assignment':True,'status':'REVIEW ONLY; unallocated/overlap groups remain HOLD'}
with gzip.open(O/'finite_window_proposal_v50.json.gz','wt') as f:json.dump({'summary':summary,'new_private_regions':placed,'cannot_fit_current_frame_within110um_target_relocation':fails,'unresolved_roles':unresolved,'control_overlap_census':ov,'control_control_overlaps':control_pairs},f,indent=1)
(O/'finite_window_summary_v50.json').write_text(json.dumps(summary,indent=2)+'\n')
fig,a=plt.subplots(figsize=(8,13));a.add_patch(Rectangle((0,0),W,H,fill=False));cols={'FT':'#538acb','stream':'#b47abe','boundary':'#dbb45b','control':'red','tload':'orange'}
for r in block[:18]:a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='green',alpha=.08,ec='green',lw=.5))
for h in T['hard_cores']:
 x,y=h['origin_um'];a.add_patch(Rectangle((x,y),121.848,62.952,fc='#ccc',ec='black'))
for z in placed:
 r=z['window_um'];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc=cols[z['kind']],alpha=.35,ec=cols[z['kind']],lw=.6))
for z in fails:a.plot(*z['desired_point'],'kx',ms=5)
for z in T['clock']['taps']:a.plot(*z['xy'],'b.',ms=2)
for k,c in cols.items():a.plot([],[],color=c,lw=5,label=k)
a.legend(fontsize=8,loc='lower right');a.set(xlim=(-8,W+8),ylim=(-8,H+8),aspect='equal',xlabel='um',ylabel='um',title=f'PRIVATE new finite native-register intent\n{summary["new_window_FFs"]:,} FFs allocated; {summary["unallocated_FFs"]:,} HOLD; {len(ov)} control overlaps\nControls-first banks occupancy ≤50%; fixed native clock points unchanged')
fig.tight_layout();fig.savefig(O/'finite_window_proposal_v50.png',dpi=145);print(json.dumps(summary),flush=True)

import json,gzip,re,math,collections,pathlib,heapq,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent
J=json.load(gzip.open(B/'original_geom.json.gz'));T=json.load(open(B/'source_type.json'));G=json.load(gzip.open(B/'native_graph_r5.json.gz'));D=J['pins'];X=json.load(open(B/'extra_pins.json'))
W,H=311.04,613.44;rim,end,gap,pad,rate=4.32,2.16,.96,.128,5.95
pitch={'M4':.048,'M5':.048,'M6':.064,'M7':.064};offset={'M4':.024,'M5':.024,'M6':.032,'M7':.032}
def snap(z,l):return round(offset[l]+round((z-offset[l])/pitch[l])*pitch[l],6)
def xy(f,q,inset=0):return [q if f in 'NS' else (inset if f=='W' else W-inset),q if f in 'EW' else (inset if f=='S' else H-inset)]
def auxbus(n):
 for p in ['fclk_in_','fclk_out_','cland_fstart_in_','cland_fstart_out_']:
  if n.startswith(p):return n[len(p):]
 return None
pins=[];windows={};usage={}
for face in 'NSEW':
 data=collections.defaultdict(list)
 for p in D:
  if p['face']==face:data[p['bus']].append(p)
 pos=rim+end
 for bus in sorted(data,key=lambda k:min(z['x'] if face in 'NS' else z['y'] for z in data[k])):
  a=data[bus];ls=collections.Counter(z['layer'] for z in a);aux=[z for z in X if z['face']==face and auxbus(z['name'])==bus]
  n7=ls.get('M7',0)+(len(aux) if face in 'NS' else 0);span=max([n7]+[v for k,v in ls.items() if k!='M7'])/rate+pad
  windows[bus]={'bus':bus,'face':face,'lo':pos,'hi':pos+span,'center':pos+span/2};lo=pos
  for layer,n in ls.items():
   order=sorted([z for z in a if z['layer']==layer],key=lambda z:z['x'] if face in 'NS' else z['y'])
   slots=list(range(n+(len(aux) if layer=='M7' and face in 'NS' else 0)));take=[]
   if layer=='M7' and face in 'NS' and aux:
    at=(len(slots)-len(aux))//2;take=slots[at:at+len(aux)];slots=[k for k in slots if k not in take]
   for z,k in zip(order,slots):
    q=snap(lo+pad/2+(k+.5)/rate,layer);xx,yy=xy(face,q);pins.append({'name':f'{bus}[{z["bit"]}]','face':face,'layer':layer,'x':xx,'y':yy,'role':'data'})
   for z,k in zip(aux,take):
    q=snap(lo+pad/2+(k+.5)/rate,'M7');xx,yy=xy(face,q,2.656);pins.append(dict(z,x=xx,y=yy,role='coupled_edge_infrastructure',paired_bus=bus))
  if face in 'EW':
   for k,z in enumerate(aux):
    q=snap(lo+span/2+(k-(len(aux)-1)/2)*8.64,'M7');xx,yy=xy(face,q,2.144);pins.append(dict(z,x=xx,y=yy,role='coupled_edge_infrastructure',paired_bus=bus))
  pos+=span+gap
 usage[face]={'data_end':pos-gap,'legal_last':(W if face in 'NS' else H)-rim-end,'end_clearance':(W if face in 'NS' else H)-rim-end-(pos-gap)}
# Non-bus control entries retain native roles; no extra ports or cycles.
ctrl=[z for z in X if z['face']!='INTERIOR' and auxbus(z['name']) not in windows]
for z in ctrl:
 y={'arst_n':367.2,'start_i':369.36,'cland_up_ready':373.68,'cland_up_fault':375.84,'fclk_out_cland_up':371.52,'cland_rstart_out':306.72}.get(z['name'])
 if y is None:raise RuntimeError('unclassified control '+z['name'])
 xx,yy=xy(z['face'],snap(y,'M7'),2.144);pins.append(dict(z,x=xx,y=yy,role='native_control'))
# Existing 4.32um site phase of constant straps is preserved exactly under lattice translation.
for z in X:
 if z['layer']=='M5' and z['face']=='INTERIOR':pins.append(dict(z,x=round(z['x']-60.48,6),y=round(z['y']-367.2,6),role='constant_count_strap'))
cland=next(z for z in X if z['name']=='cland_tstart_in');pins.append(dict(cland,x=207.392,y=315.36,role='collector_start'))
macros=[{'name':f'm{i}','inst':f'u_bound.u_core.u_tload.u_ld.m{i}','rect':[60.48,y,182.328,y+62.952],'halo_rect':[56.16,y-4.32,186.648,y+67.272]} for i,y in enumerate([142.56,237.6,332.64,427.68])]
bands={
 'cws1_i':[73.44,501.12,177.12,592.56], 'flt_ctl_i':[60.48,508.32,69.12,592.56],
 'x_ctl_fw_p1_i':[185.76,522.72,306.72,609.12], 'x_ctl_i':[47.52,508.32,56.16,592.56],
 'x_fe_i':[190.08,17.28,293.76,110.16], 'x_fe_fw_i':[190.08,123.12,293.76,216.0],
 'x_fe_fw_p1_i':[190.08,217.08,293.76,309.96], 'x_fe_p1_i':[190.08,427.68,293.76,520.56],
 'x_sc_fw_i':[207.36,371.52,293.76,380.16], 'x_su_c_ctl_i':[43.2,17.28,60.48,86.4],
 'x_su_l0_i':[60.48,17.28,99.36,129.6], 'x_su_l1_i':[99.36,17.28,138.24,129.6]}
capboxes={f'm{i}':[25.92,m['rect'][1]+10.8,47.52,m['rect'][1]+43.2] for i,m in enumerate(macros)};relay=[17.28,475.2,51.84,501.12]
btw=windows['b_tw_data_ctl_o'];publication=[btw['lo'],596.16,btw['hi'],609.12]
def center(r):return [(r[0]+r[2])/2,(r[1]+r[3])/2]
def area(r):return (r[2]-r[0])*(r[3]-r[1])
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-7 and min(a[3],b[3])>max(a[1],b[1])+1e-7
def bound_l1(a,b):return max(abs(x-u)+abs(y-v) for x in [a[0],a[2]] for y in [a[1],a[3]] for u in [b[0],b[2]] for v in [b[1],b[3]])
def insidept(p,r,clear=0):return r[0]-clear<=p[0]<=r[2]+clear and r[1]-clear<=p[1]<=r[3]+clear
# All ROM/landing/capture rectangles describe ENTIRE cell bounding boxes. Top609.12 is not a legal cell bottom.
old={n:z['rect_um'] for n,z in T['clock']['landing_contract']['bands'].items()}
recterrors=[]
for name,r in bands.items():
 if area(r)+1e-6<area(old[name]):recterrors.append('reduced inherited band area '+name)
 for m in macros:
  if overlap(r,m['halo_rect']):recterrors.append('band/macrohalo '+name+'/'+m['name'])
for k,a in enumerate(list(bands)):
 for b in list(bands)[k+1:]:
  if overlap(bands[a],bands[b]):recterrors.append('bands overlap '+a+'/'+b)
# Existing native FF chains establish registered-edge count; these are PROPOSED target boxes, not placed coordinates.
segment_bounds={}
for i,m in enumerate(macros):
 # Actual LEF signal pins are westM4 fromy~0.77 to~27.55; boundwholewestedge conservatively.
 r=m['rect'];romport=[r[0],r[1],r[0]+.024,r[3]]
 segment_bounds[m['name']]={'ROM_to_loader_capture_bound_um':bound_l1(romport,capboxes[m['name']]),'loader_to_core_capture_bound_um':bound_l1(capboxes[m['name']],relay),'core_to_N_publication_bound_um':bound_l1(relay,publication),'registered_edges':3}
# Infer stream-bank target centers from actual native sequential graph and actual primary/publication interfaces.
priors={};banks=G['stream_native_bank_counts'];deps=G['stream_native_bank_dependencies'];adj=collections.defaultdict(collections.Counter)
for a,ss in deps.items():
 for b,n in ss.items():adj[a][b]+=n;adj[b][a]+=n
for b in banks:
 points=[]
 for field in ['stream_native_primary_input_support','stream_native_publication_support']:
  for port,n in G[field].get(b,{}).items():
   if port in windows:points.append((xy(windows[port]['face'],windows[port]['center'],12.96),n))
 if points:
  priors[b]=[sum(p[k]*n for p,n in points)/sum(n for p,n in points) for k in (0,1)]
pos={b:priors.get(b,[155.52,306.72])[:] for b in banks}
for _ in range(80):
 nxt={}
 for b in banks:
  if b in priors:nxt[b]=priors[b];continue
  ss=adj[b];tot=sum(ss.values());nxt[b]=[sum(pos[a][k]*n for a,n in ss.items())/tot for k in (0,1)] if tot else pos[b]
 pos=nxt
# Coarse consumer target sites avoid macro halos and non-owned landing reserves. They are estimates, not achieved placement.
free=[(x,y) for x in [17.28+8.64*i for i in range(33)] for y in [17.28+10.8*i for i in range(54)] if x<W-17.28 and y<H-17.28 and not any(insidept((x,y),m['halo_rect'],2.16) for m in macros) and not any(insidept((x,y),r,1.08) for r in bands.values())]
def nearfree(p):return min(free,key=lambda z:abs(z[0]-p[0])+abs(z[1]-p[1]))
streampos={b:nearfree(p) for b,p in pos.items()}
# Existing FT stationcount is retained; derive proposedZ-route station targets from new exactportwindows, no addedstages.
ft={}
def sampleline(points,f):
 lens=[abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(points,points[1:])];rem=sum(lens)*f
 for a,b,L in zip(points,points[1:],lens):
  if rem<=L+1e-8:return [a[k]+(b[k]-a[k])*(rem/L if L else 0) for k in (0,1)]
  rem-=L
 return points[-1]
for z in T['ft_slots']:
 si=windows[z['name']+'_i'];so=windows[z['name']+'_o'];a=xy(si['face'],si['center'],12.96);b=xy(so['face'],so['center'],12.96)
 path=[a,[(a[0]+b[0])/2,a[1]],[(a[0]+b[0])/2,b[1]],b] if si['face'] in 'EW' and so['face'] in 'EW' else [a,[a[0],b[1]],b]
 ft[z['name']]=[nearfree(sampleline(path,i/z['stations'])) for i in range(z['stations'])]
romcaplookup={n:bank.rsplit('.',1)[-1] for bank,ns in G['ROM_first_capture_cells'].items() for n in ns}
def bankof(n):return re.sub(r'\[\d+\]','[*]',n.split('u_stream.',1)[1].split('$_')[0])
def anchor(n):
 if n in romcaplookup:return center(capboxes[romcaplookup[n]])
 if n.startswith('u_bound.u_core.u_stream.'):return streampos[bankof(n)]
 if n.startswith('u_bound.u_core.u_tload.'):return center(capboxes['m3'])
 if n.startswith('u_bound.u_core.'):return center(relay)
 for bus,r in bands.items():
  if n.startswith('u_bound.u_cland_'+bus+'.') or re.match(r'u_bound\.u_pd\d+_'+re.escape(bus)+r'_\d+\.',n):return center(r)
 m=re.match(r'u_bound\.u_ft_(.+)_o_(\d+)\.',n)
 if m and m[1] in ft and int(m[2])<len(ft[m[1]]):return ft[m[1]][int(m[2])]
 m=re.match(r'u_bound\.u_b(?:in|out)_(.+)\.',n)
 if m and m[1] in windows:
  z=windows[m[1]];return xy(z['face'],z['center'],12.96)
 # Actual small collector/reset/start modules sharetheprimarycontrollerwindow; thisisexplicitproposedplacement, notoldpointprojection.
 return [207.36,306.72]
FF=G['local_clock_cells'];hist=collections.defaultdict(list)
for n in FF:
 p=anchor(n);hist[(round(p[0],3),round(p[1],3))].append(n)
clusters=[]
for p,ns in hist.items():
 for i in range(0,len(ns),600):clusters.append({'p':list(p),'cells':ns[i:i+600],'bbox':[p[0],p[1],p[0],p[1]]})
def merge(a,b):
 na,nb=len(a['cells']),len(b['cells']);p=[(a['p'][k]*na+b['p'][k]*nb)/(na+nb) for k in (0,1)];box=[min(a['bbox'][0],b['bbox'][0]),min(a['bbox'][1],b['bbox'][1]),max(a['bbox'][2],b['bbox'][2]),max(a['bbox'][3],b['bbox'][3])]
 return {'p':p,'cells':a['cells']+b['cells'],'bbox':box}
while len(clusters)>76:
 best=None
 for i,a in enumerate(clusters):
  for k in range(i+1,len(clusters)):
   b=clusters[k]
   if len(a['cells'])+len(b['cells'])>1100:continue
   q=merge(a,b)
   if bound_l1(q['bbox'],[q['p'][0],q['p'][1],q['p'][0],q['p'][1]])>140:continue
   score=abs(a['p'][0]-b['p'][0])+abs(a['p'][1]-b['p'][1])
   if best is None or score<best[0]:best=(score,i,k,q)
 if best is None:raise RuntimeError('cannotform76localclockgroups under1100load/140umestimatedradius')
 _,i,k,q=best;clusters[i]=q;clusters.pop(k)
if len(clusters)!=76:raise RuntimeError('clockgroupcount '+str(len(clusters)))
# M7mesh-entrybays remain>=17.28fromoutline, phaseclear ofM5/M6/M7PGstripes; actualPVTbudget unchanged.
strapbox=[224.64,280.8,276.48,328.32]
sites=[(round(.032+8.64*i,6),round(.032+8.64*k,6)) for i in range(2,34) for k in range(2,70) if .032+8.64*i<W-17.248 and .032+8.64*k<H-17.248]
sites=[p for p in sites if not any(insidept(p,m['halo_rect'],2.16) for m in macros) and not insidept(p,strapbox,4.32)]
used=set();clockassign={};available=set(range(76))
def takeclock(name,want):
 choices=[]
 for i in available:
  c=clusters[i];cand=[p for p in sites if p not in used and bound_l1(c['bbox'],[p[0],p[1],p[0],p[1]])<=200]
  if not cand:continue
  p=min(cand,key=lambda p:abs(p[0]-want[0])+abs(p[1]-want[1]))
  choices.append((abs(c['p'][0]-want[0])+abs(c['p'][1]-want[1]),i,p))
 if not choices:raise RuntimeError('noclockbay '+name)
 _,i,p=min(choices);c=clusters[i];available.remove(i);used.add(p)
 clockassign[name]={'pin_xy_um':list(p),'M7_pin_size_um':[.032,.768],'clock_buffer_bay_um':[p[0]-2.16,p[1]-2.16,p[0]+2.16,p[1]+2.16],'actual_named_local_FF_count':len(c['cells']),'actual_named_local_FFs':c['cells'],'estimated_consumer_bbox_um':c['bbox'],'estimated_max_L1_consumer_anchor_to_entry_um':bound_l1(c['bbox'],[p[0],p[1],p[0],p[1]]),'source_type_default_insertion_ps':250,'source_type_default_tolerance_ps':40,'effective_per_port_timing_contract':'retain exact frozen clock_binding.json/constraint.sdc values; no per-port source offsets or achieved delays inferred','status':'estimatedproposedgeometry; actualpostPLACEconsumer/cap/clockGEOMrequired'}
 # Convertpreexistingactualpinrole, don'tinventnewABI.
 z=next(x for x in X if x['name']==name);pins.append(dict(z,x=p[0],y=p[1],role='local_clock_entry'))
takeclock('clk',[207.36,306.72])
wants=collections.defaultdict(list)
for z in T['clock']['landing_contract']['pins']:
 if z['name'].startswith('fclk_out_') and z.get('source_clock_tap'):
  bus=z['name'][len('fclk_out_'):]
  if bus in windows:wants[z['source_clock_tap']].append(xy(windows[bus]['face'],windows[bus]['center'],17.28))
for name,ps in sorted(wants.items()):takeclock(name,[sum(p[k] for p in ps)/len(ps) for k in (0,1)])
for i in range(1,76):
 name='clk_t'+str(i)
 if name not in clockassign:
  k=min(available);takeclock(name,clusters[k]['p'])
assert len(pins)==17874 and len({p['name'] for p in pins})==17874
assert sum(z['actual_named_local_FF_count'] for z in clockassign.values())==52609
assert len(set(n for z in clockassign.values() for n in z['actual_named_local_FFs']))==52609
# Exactinclusive10umslidingedgeprojection includingco-locatedforwardedclock/startcontacts, notonlyaveragedensity.
def maxwin(a):
 a=sorted(a);i=0;mx=0
 for k,x in enumerate(a):
  while x-a[i]>10+1e-8:i+=1
  mx=max(mx,k-i+1)
 return mx
census=[]
for f in 'NSEW':
 for l in ['M4','M5','M6','M7']:
  q=[p for p in pins if p['face']==f and p['layer']==l and p['role'] not in ['local_clock_entry','constant_count_strap','collector_start']]
  if q:census.append({'face':f,'layer':l,'count':len(q),'max_inclusive10um':maxwin([p['x'] if f in 'NS' else p['y'] for p in q]),'limit':60})
rows={}
for name,r in dict(capboxes,core_publication=relay,N_boundary=publication).items():
 rows[name]={'ENTIRE_cell_bbox_window_um':r,'row_height_um':.27,'regularFF_width_um':1.08,'resetFF_width_um':1.404,'max_cell_bottom_y_um':r[3]-.27,'conservative_2p16column_FF_slots':math.floor((r[2]-r[0])/2.16)*round((r[3]-r[1])/.27),'row_orientation':'readactualODBroworientation R0/MX; no assumedrowflip or cellbottomattopendpoint'}
field={'outline_um':[W,H],'aspect':H/W,'source_sha':'d90b10921','scope':'PRIVATEestimatedgeometricallocation ONLY; noadoptedplan/P&R/SIGNED/EQtransfer','all_native_pin_bits':len(pins),'native_data_bits':17671,'native_edge_aux_bits':52,'native_interior_aux_bits':151,'pins':pins,'windows':windows,'edge_usage':usage,'edge_sliding10um_census':census,'macros':macros,'landing_bands_entire_cell_bbox_um':bands,'landing_rectangle_errors':recterrors,'ROM_capture_boxes':capboxes,'core_publication_relay_box':relay,'N_publication_box':publication,'existing3edge_segment_bounding_um':segment_bounds,'capture_row_constraints':rows,'clock_assignments':clockassign,'local_clock_nativeFF_total':52609,'ROM_clock_consumers':G['ROM_clock_roots'],'native_clock_export_roots_beforephysicalhook':G['clock_export_roots'],'other_clock_gate_input_incidences':G['other_clock_only_primitive_inputs'],'forwarded_clock_nativeFF_counts':{k:v for k,v in G['clock_ff_counts'].items() if k!='clk'},'forwarded_CTS_model_branches_at1200':{k:math.ceil(v/1200) for k,v in G['clock_ff_counts'].items() if k!='clk'},'std_fill_free_nominal':J['fill']['stdcell_lef_area_um2']/((W-8.64)*(H-8.64)-J['fill']['rom_lef_area_um2']),'macro_signal_escape':{'west_M4_perbank_height_um':32.4,'at60pct_tracks':405,'terminal_upperbound_perbank':280,'vertical_ROM_corridor_um':[17.28,51.84],'existing_internal_vertical_layers':['M3','M5','M7'],'at60pct_vertical_tracks':1332,'ROM_publication_bit_upperbound':1064,'M5_M7alone_tracks':756,'M5_M7alone_wouldfail_798bitcut':True},'holds':['actualplacement/clockGEOM/firstcapturep90/PGconnectivity/detailedescape remainUNMEASURED','sourceoffsets/insertiontargets/profiles/params/cycles/ROMviewadoptionUNCHANGED; noachievedclocklatencyguessed','allneighbourport/parentclockmesh/strap/dropallocationmustbecomposedandreviewedbeforeGEN/PLACE','actualselectedROMparams/assets/namespace mustqualify independently; existingTT/LEF/PPAprototypeONLY noarchivedMIF1functionalcredit']}
(B/'private_proposal_v2.json').write_text(json.dumps(field,indent=1));summary={k:v for k,v in field.items() if k not in ['pins','clock_assignments']};summary['clock_load_model']={n:{k:v for k,v in z.items() if k!='actual_named_local_FFs'} for n,z in clockassign.items()};(B/'proposal_v2_summary.json').write_text(json.dumps(summary,indent=2))
fig,ax=plt.subplots(figsize=(8,12));ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.4))
for n,r in bands.items():ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='#d8eff0',ec='#5b9195',alpha=.55,lw=.6));ax.text(*center(r),n,fontsize=4.5,ha='center')
for m in macros:
 r=m['rect'];h=m['halo_rect'];ax.add_patch(Rectangle((h[0],h[1]),h[2]-h[0],h[3]-h[1],fill=False,ls=':',ec='gray'));ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='#afb7be',ec='black',lw=.8));ax.text(*center(r),m['name'],ha='center',fontsize=9)
for n,r in dict(capboxes,coreRelay=relay,Npublication=publication).items():ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,ec='#ed8b23',lw=.7))
for layer,color in {'M4':'#205ca8','M5':'#319b77','M6':'#ba5a1b','M7':'#9a389f'}.items():
 q=[p for p in pins if p['layer']==layer and p['role']!='local_clock_entry'];ax.scatter([p['x'] for p in q],[p['y'] for p in q],s=.4,color=color,label=layer)
ax.scatter([z['pin_xy_um'][0] for z in clockassign.values()],[z['pin_xy_um'][1] for z in clockassign.values()],s=12,color='red',marker='+',label='76estimatedclockentries')
ax.text(157,342,'PRIVATE — NOT physicalqualification\n17874actualnamedpinbitsallocated\n76nonemptyestimatedclockgroups\n3EXISTINGROMpublicationedges\nNo source/timingoffset/profilechange\nActualPLACE/clockGEOM/PG/escapeHELD',fontsize=7,ha='center',bbox={'fc':'white','ec':'red','alpha':.85})
ax.set(xlim=(-12,W+12),ylim=(-12,H+12),xlabel='µm',ylabel='µm',title='slw_stm_v3 private one-column geometric proposal\n311.04×613.44µm; 20.266% nominalfreefill; aspect1.972');ax.set_aspect('equal');ax.legend(loc='lower right',fontsize=6);fig.tight_layout();fig.savefig(B/'proposal_v2.png',dpi=170);plt.close(fig)
print('V2',len(pins),'pins',len(clockassign),'nonemptyclockgroups','maxFFload',max(z['actual_named_local_FF_count'] for z in clockassign.values()),'maxestclockreach',max(z['estimated_max_L1_consumer_anchor_to_entry_um'] for z in clockassign.values()),'recterrors',recterrors,'maxedgewindow',max(z['max_inclusive10um'] for z in census))

# Review contract supplements are separately explicit; no inferred library/source timing values.
field.update(json.load(open(B/'static_geometry_contract.json')))
(B/'private_proposal_v2.json').write_text(json.dumps(field,indent=1)+'\n')
with gzip.GzipFile(str(B/'private_proposal_v2.json.gz'),'wb',mtime=0) as gz:
 gz.write((B/'private_proposal_v2.json').read_bytes())

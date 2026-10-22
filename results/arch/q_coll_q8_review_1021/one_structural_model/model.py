#!/usr/bin/env python3
"""One source/geometry proposal, no active kit edits or EDA invocation."""
from pathlib import Path
import json,re,math,hashlib,collections
ROOT=Path('/home/ubuntu/wt/qko-coll-1021');HERE=Path(__file__).resolve().parent
A=Path('/home/ubuntu/scratch/q8a-net42538-1021');B=Path('/home/ubuntu/scratch/q8b-net10846-1021')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
fp=json.loads((ROOT/'physical/ref_tile/qfd_coll_split_q8a/floorplan.json').read_text());spec=json.loads((ROOT/'physical/ref_tile/qfd_coll_split_q8a/spec.json').read_text())
# Measured stored GCell axes, not a guessed metal pitch.
def dump(p):
 r=[x.split('\t')for x in p.read_text().splitlines()];gx=list(map(int,next(v[1]for v in r if v[0]=='GRIDX').split()));gy=list(map(int,next(v[1]for v in r if v[0]=='GRIDY').split()));g={(v[1],int(v[2]),int(v[3])):(float(v[4]),float(v[5]))for v in r if v[0]=='GRID'};return r,gx,gy,g
ra,gxa,gya,ga=dump(A/'dump.log');rb,gxb,gyb,gb=dump(B/'dump.log');pitches=set(b-a for a,b in zip(gxa,gxa[1:]));assert pitches=={570};G=.570
# Real native LEF families: MY does not put all SRAM ports on the inner face.
lef={};pinmaps={}
for dep in [128,256]:
 p=A/f'inputs/ot_sram_1r1w2c_{dep}x64_m1.lef';s=p.read_text();w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',s).groups());pins={}
 for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1',s,re.S):
  q=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2]);bb=list(map(float,q.groups()));pins[m[1]]=dict(side='W'if(bb[0]+bb[2])/2<w/2 else'E',bbox=bb)
 pinmaps[dep]=pins;lef[dep]=dict(path=str(p),sha256=sha(p),w=w,h=h,canonical_face_counts={side:dict(collections.Counter(re.sub(r'\[.*','',n)for n,v in pins.items()if v['side']==side))for side in ['W','E']})
# Exact original mapped macro WD connections -> distinct outer W-facing payload signals.
v=(A/'1_2_yosys.v').read_text();assert sha(A/'1_2_yosys.v')=='68b2d033b4603e1ce949fe697ea27bbd34b341981884c40f623839033814b1f5';start=v.index('module ot_coll_split_q_native32(');v=v[start:v.index('endmodule',start)];macros={}
for m in re.finditer(r'^  (ot_sram_1r1w2c_(128|256)x64_m1)\s+(\S+)\s*\(\n(.*?)\n  \);',v,re.M|re.S):macros[m[3]]=dict(depth=int(m[2]),ports=dict(re.findall(r'\.(\w+)\((.*?)\)',m[4])))
outer_payload=set();outer_rows=[]
for name,m in macros.items():
 if not(name.startswith(r'\u_sd.')or name==r'\u_pring.g_b[1].u_m'):continue
 bits=[x.strip()for x in m['ports']['wd_in'].strip('{} ').split(',')];selected=[]
 for pn,p in pinmaps[m['depth']].items():
  if pn.startswith('wd_in[')and p['side']=='E':
   bit=int(re.search(r'\[(\d+)\]',pn)[1]);net=bits[-1-bit];outer_payload.add(net);selected.append(dict(pin=pn,signal=net))
 outer_rows.append(dict(instance=name,MY_outer_W_payload=selected,mask_note='w_mask pins also outer W; source mapped _05108_ is TIEHI, preserve actual local tie splitting/PG and pin access; not a global data crossing'))
assert len(outer_rows)==5 and len(outer_payload)==125
caps=[]
for edge,yr,gx,gy,g in [(43.2,(175.152,216.504),gxa,gya,ga),(47.52,(65.136,106.488),gxb,gyb,gb)]:
 samples=[]
 for(l,x,y),(cap,use)in g.items():
  if l=='M3'and edge-2.88<=gx[x]/1000<edge and yr[0]<=gy[y]/1000<=yr[1]and('M5',x,y)in g:samples.append(cap+g[('M5',x,y)][0])
 caps.append(min(samples))
C=min(caps);columns=math.ceil(len(outer_payload)/C);stripe=(columns+3)*G # five full payload cells + two guards + arbitrary-grid-phase cell
assert columns==5 and abs(stripe-4.56)<1e-9
# Current 64um pair ranges cannot fit actual intergroup cuts.
columns_old={}
for block in fp['blocks']:columns_old.setdefault(block['x'],[]).append(block)
groups={}
for x,blocks in columns_old.items():
 blocks=sorted(blocks,key=lambda b:b['y']);gg=[]
 for b in blocks:
  if not gg or b['y']-(gg[-1][-1]['y']+gg[-1][-1]['h'])>20:gg.append([])
  gg[-1].append(b)
 groups[x]=gg
assert sorted(len(g)for g in groups.values())==[3,3]
# Preserve real macro X/orientation and each 48nm legal origin phase. Four 128b bands,
# one per opening; 4pins/um is the existing source policy, no pin-density increase.
M=.048;framegrid=2.16;core=2.16;band=128/4;corner=math.ceil((1.0+4*.27)/.216)*.216
assert abs(corner-2.16)<1e-9
ceilgrid=lambda n,g:round(math.ceil((n-1e-9)/g)*g,6)
proposed=[];openings={};heights=[]
for x,gg in groups.items():
 y=core;oo=[]
 for gi,group in enumerate(gg):
  needed=band+2*G+(corner if gi==0 else 0);origin=ceilgrid(y+needed,M);oo.append(dict(lo=y,hi=origin,pin_lo=y+G+(corner if gi==0 else 0),pin_hi=y+G+(corner if gi==0 else 0)+band))
  y=origin
  for i,old in enumerate(group):
   if i:y=ceilgrid(y,M)
   b=dict(old);b['y']=y;proposed.append(b);y=round(y+old['h'],6)
 oo.append(dict(lo=y,hi=y+band+2*G+corner,pin_lo=y+G,pin_hi=y+G+band));openings[str(x)]=oo;heights.append(oo[-1]['hi']+core)
H=ceilgrid(max(heights),framegrid);W=spec['outline']['w'];assert H==334.8
# Exact rectangle non-overlap and legal retained 48nm origin phase, within the core.
for b in proposed:
 assert 0<=b['x']and b['x']+b['w']<=W and core<=b['y']and b['y']+b['h']<=H-core
 assert abs(b['y']/M-round(b['y']/M))<1e-6
for i,a in enumerate(proposed):
 for b in proposed[i+1:]:assert a['x']+a['w']<=b['x']or b['x']+b['w']<=a['x']or a['y']+a['h']<=b['y']or b['y']+b['h']<=a['y']
left,right=sorted(groups);pin_ranges={}
for x,names in [(left,['sx1_data','sr1_data','sx2_data','sr2_data']),(right,['up_data','dp_data','ur_data','dr_data'])]:
 for o,name in zip(openings[str(x)],names):assert o['pin_hi']<=o['hi']-G+1e-9;pin_ranges[name]=[o['pin_lo'],o['pin_hi']]
# Capacity ledger is a ceiling from saved grid, NOT after-obstruction free-track proof.
clear_rows=min(math.floor((o['hi']-o['lo']-2*G-G)/G+1e-8)for oo in openings.values()for o in oo) # phase-safe full-cell lower bound
horizontal=clear_rows*(14+12);ledger=128+125+128+128 # data band + all outer WD payload + <=one clock/reset connection per endpoint
assert horizontal>ledger
# Explicit selected-net polylines, layer-aware around macro interiors. Exact detailed
# route legality is OPEN; knots are corridor model coordinates, not new EDA sites.
hub=[W/2,H/2];ap=openings[str(left)][1];via_y=round((ap['lo']+ap['hi'])/2,6);spine_x=round(left-stripe/2,6)
paths=[]
def add(label,p):paths.append(dict(name=label,points=p,length_um=round(sum(abs(a[0]-b[0])+abs(a[1]-b[1])for a,b in zip(p,p[1:])),6)))
# q8a hold42540->_06451 source remapped to actual sr2 band; unchanged logic/polarity.
sr2=pin_ranges['sr2_data'];add('q8a observed SerDes-capture segment',[ [43.1285,sum(sr2)/2],[88.77,sum(sr2)/2],[88.77,hub[1]] ])
for bank in [0,1]:
 pat=f'*u_sd*g_d?{bank}?*g_c?1?*u_m';b=next(b for b in proposed if b['inst']==pat);add(f'q8b WD123 -> SRAM bank{bank}wd59',[hub,[hub[0],via_y],[spine_x,via_y],[spine_x,b['y']+4.332],[left+.012,b['y']+4.332]])
add('q8b WD123 -> existing face-buffer region',[hub,[hub[0],58.725],[94.443,58.725]])
assert all(p['length_um']<405 for p in paths)
# Parse actual LEF OBS, transform MY exactly, and check selected segment centerlines.
# This deliberately excludes via enclosures/spacing/PG/other-net occupancy: no DRC claim.
obs_by_depth={}
for dep in [128,256]:
 text=Path(lef[dep]['path']).read_text().split('  OBS\n',1)[1].split('  END',1)[0]
 layer=None;obs=[]
 for line in text.splitlines():
  lm=re.search(r'LAYER (M\d+)',line)
  if lm:layer=lm[1]
  rr=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',line)
  if rr:obs.append((layer,list(map(float,rr.groups()))))
 obs_by_depth[dep]=obs
obstacles=[]
for b in proposed:
 dep=256 if '256x64' in b['master'] else 128
 assert abs(b['w']-lef[dep]['w'])<1e-8 and abs(b['h']-lef[dep]['h'])<1e-8
 for layer,(x0,y0,x1,y1) in obs_by_depth[dep]:
  assert b['orient'] in ['R0','MY']
  if b['orient']=='MY':x0,x1=b['w']-x1,b['w']-x0
  obstacles.append((layer,[b['x']+x0,b['y']+y0,b['x']+x1,b['y']+y1],b['inst']))
for path in paths:
 path['centerline_OBS_check']='PASS against retained actual LEF OBS only; no via/spacing/PG/free-track proof'
 path['segments']=[]
 for a,b in zip(path['points'],path['points'][1:]):
  is_horizontal=a[1]==b[1];layer='M4' if is_horizontal else 'M3'
  assert is_horizontal or a[0]==b[0]
  for ol,(x0,y0,x1,y1),inst in obstacles:
   if ol!=layer:continue
   hit=(y0<a[1]<y1 and max(min(a[0],b[0]),x0)<min(max(a[0],b[0]),x1)) if is_horizontal else (x0<a[0]<x1 and max(min(a[1],b[1]),y0)<min(max(a[1],b[1]),y1))
   assert not hit,(path['name'],layer,inst,a,b)
  path['segments'].append(dict(layer=layer,start=a,end=b))

# Preserve full-family evidence: q8b soft flops fail even if only macros were fixed.
clocks={}
for tag in ['q8a','q8b']:
 j=json.loads((HERE.parent/tag/'gate_result.json').read_text());c=j['clock'];m=c['clock_measurements'][0];clocks[tag]={k:c[k]for k in ['verdict','tt_spread_ps','ff_spread_ps','tt_pin_spread_ps','ff_pin_spread_ps']}
 for corner_ in ['tt','ff']:
  z=m[corner_];sp=z['child_flop']['soft']['all'];pins=z['macros']['pins'];clocks[tag][corner_]=dict(soft=sp,soft_spread=round(sp['max']-sp['min'],3),macro_min=min(pins,key=lambda p:p['arr']),macro_max=max(pins,key=lambda p:p['arr']))
result={'verdict':'ONE_MODEL_FOR_ROOT_REVIEW_NOT_READY_FOR_GATE','scope':'No active source/kit edit, RTL edge, probe, map, router, gate or variant. One q8a-derived pin-contained geometry plus durable data-role placement and full-family clock proposal.','source_commit':'a153761f95cee63943c1c363ec80ccc9c4344b8a','inputs':{'q8a_geometry_sha':'813912b54b227005639eda9eb1af6e99f6c7a16e9d9a7c16e9d9a7c89f185dac5bc880a18','q8a_floorplan_sha256':sha(ROOT/'physical/ref_tile/qfd_coll_split_q8a/floorplan.json'),'q8a_spec_sha256':sha(ROOT/'physical/ref_tile/qfd_coll_split_q8a/spec.json'),'q8a_dump_sha256':sha(A/'dump.log'),'q8b_dump_sha256':sha(B/'dump.log'),'mapped_source_sha256':sha(A/'1_2_yosys.v')},'existing_pin_band_mismatch':{'W_pair_span_um':64,'q8a_actual_internal_cut_um':27.288,'q8b_actual_internal_cut_um':23.0,'required_two_bus_band_um':64.0,'policy_pins_per_um':4,'old_declared_pin_ranges':spec['pin_ranges']},'actual_LEF':lef,'MY_outer_payload_unique_nets':len(outer_payload),'MY_outer_payload_connections':outer_rows,'measured_gcell_pitch_um':G,'capacity_model':{'stored_M3_plus_M5_sample_min':[float(v)for v in caps],'payload_tracks_required':len(outer_payload),'full_vertical_gcells_required':columns,'stripe_um':stripe,'stripe_derivation':'(ceil(125/27)+3)*0.570 =4.560; two GCell edge guards plus one unknown-phase GCell; guarantees five full payload columns in an empty corresponding strip','raw_vertical_capacity_ceiling':columns*C,'phase_safe_full_aperture_rows':clear_rows,'raw_M2_M4_capacity_ceiling':horizontal,'partial_per_aperture_connection_ledger':ledger,'ledger_detail':'PARTIAL ledger only:128banddata+125allouterWD+128clock+128reset endpoint connections. NOT a full traffic/cut or required-track certificate; other selection/read/control nets, local mask-tie stubs, actual clock topology, metal and PG remain uncounted. Source one-register-per-boundary-bit assumption must remain enforced.','free_capacity_status':'UNPROVEN. Stored grid capacity is a ceiling, not actual free tracks after PG, temporary hook shapes, repair and other nets. Reservation/guide enforcement must be implemented and checked, no legal-route claim.'},'proposed_outline_um':{'w':W,'h':H},'proposed_core_um':[core,core,W-core,H-core],'proposed_macro_blocks':proposed,'proposed_openings':openings,'proposed_pin_ranges':pin_ranges,'pin_aperture_derivation':'128/4=32um band + one measured0.570GCell guard at each end; outer apertures also exclude2.160um initial orthogonal IO-flop depth (1+4*0.27 rounded to0.216). Macro origins retain48nm lattice; frame rounds2.160um. No increased pin density.','outer_W_payload_strip_um':[left-stripe,left],'placement_contract':'IO first/last registers and their actual transparent repair descendants must stay in their own clear aperture corridor; all ordinary non-IO arithmetic/selection remains in the inner core bay. Dedicated outer-W WD spine/data stubs must retain access, with local tie cells/endcaps/PG explicitly handled. Initial FIRM anchoring then release toPLACED is insufficient. Do not place hard blockages over existing macro halo/endcaps. This durable region/guide implementation is not supplied by current kit.','selected_paths':paths,'selected_path_scope':'Only observed failing segment and WD123 bank/face branches are geometrically bounded below405; corridor knots are not detailed routing sites. Not an all-native-hop/reach or timing proof.','clock_evidence':clocks,'clock_proposal':'Keep clock source/frequency/SDC/edge semantics and q8a source as pinned comparison. Build physical balanced leaf clusters for the four IO-aperture endpoint groups, ordinary core registers, and all12dual-clock SRAMs under the SAME root. Balance actual TT and FF all-register+all-macro endpoint union, not boundary-only or macro-only. Region durability must include clock/hold repair; no delay exception/phase/multicycle/new state. Existing generic SYM/SAFE_BALANCE flags alone do not establish this.','blocking_unmodelled_clock_gap':'Existing ck.json only gives standard-cell aggregate extrema, not their identities/per-leaf membership, branch RC/cap or TT/FF leaf windows. q8b SOFT spans113.7/111.4 already exceed80, so macro-only fixes cannot qualify. Cannot derive legal physical buffer sizes/counts or new334.8um-frame clock spread from current data. Need exact existing clock-tree/leaf/sink raw data before admitting this single proposal; q8a48.7/51.9 is no transfer PASS.','blocking_unmodelled_routing_gap':'30 transient hook shapes and failed maze heap removed. Existing snapshots identify endpoints/OBS/grid but cannot certify full after-PG/transient multi-net capacity or repair-created buffer placement. Actual durable region/guide allocator + all affected branch/access occupancy must be demonstrated before any unchanged gate retry.','qualification':'OPEN: no physical/gate/schedule/native/clock improvement claimed; no further job authorized by this artifact.'}
# Bind read-only technology extraction to original image provenance. No EDA ran.
snapshot=json.loads(Path('/tmp/ref_gate_qfd_coll_split_q8b_20261021-133920.source_snapshot.json').read_text())
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
assert any(image in str(x) for x in snapshot['runtime_tool_provenance'])
result['technology_source']={'original_image':image,'extraction':'read-only /bin/cat of actual OCI image files, no design load or EDA invocation','tech_lef':{'original_path':'/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef','retained_sha256':sha(HERE/'actual_image_tech.lef')},'make_tracks':{'original_path':'/OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl','retained_sha256':sha(HERE/'actual_make_tracks.tcl')},'directions':'M2/M4 horizontal; M3/M5 vertical. M6 excluded by existing top-M5 tile rule. Physical track grids do not establish after-PG free GCell capacity.'}
# Correct immutable q8a geometry identity from its original receipt.
result['inputs']['q8a_geometry_sha']=json.loads((HERE.parent/'q8a/REVIEW.json').read_text())['geometry_sha256']
(HERE/'PROPOSAL.json').write_text(json.dumps(result,indent=2)+'\n');print('ONE_MODEL',W,H,'payload',len(outer_payload),'stripe',stripe,'aperture ceiling',horizontal,'ledger',ledger,'paths',[(p['name'],p['length_um'])for p in paths]);print('NOT_READY_FOR_GATE: actual free-capacity and full clock-leaf model remain OPEN')

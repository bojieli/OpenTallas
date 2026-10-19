import collections,copy,gzip,hashlib,json,math,pathlib,re
H=pathlib.Path(__file__).resolve().parent
P=H.parent/'s81_sh3ebb_fixedpoint_model_1019'
d=json.load(gzip.open(P/'graph.json.gz','rt')); rs=copy.deepcopy(d['records']);masters=d['masters']
def inst(pin): return pin.rsplit('/',1)[0]
roots={r['driver']:r for r in rs}; incoming={e['pin']:(r,e) for r in rs for e in r['endpoints']}
# Retain all roots of a multi-output master; never select only its last output.
def fixed(records):
 by=collections.defaultdict(list)
 for r in records:
  if r['role'] not in ('input','macro'):by[inst(r['driver'])].append(r)
 copies={n:1 for n in by};rounds=[]
 for _ in range(100):
  nxt={n:max(copies[n],max(math.ceil(sum(copies.get(inst(e['pin']),1) for e in r['endpoints'])/32) for r in rr)) for n,rr in by.items()}
  rounds.append(sum(v-1 for v in nxt.values()))
  if nxt==copies:break
  copies=nxt
 else:raise AssertionError('no fixed point')
 for r in records:assert sum(copies.get(inst(e['pin']),1) for e in r['endpoints'])<=32*copies.get(inst(r['driver']),1)
 return by,copies,rounds
oldby,oldcopies,oldrounds=fixed(rs)
predicates=[];rnowner=None
for port in ['f_host[0]','f_ks[52]','kd_i[53]','j_i[32]','s_jd_w[0]','s_jd_w[1]','s_jd_e[0]','s_jd_e[1]']:
 raw=roots['PORT/'+port]; assert len(raw['endpoints'])==1
 gatepin=raw['endpoints'][0]['pin']; gate=next(r for r in rs if inst(r['driver'])==inst(gatepin)); assert gate['master'].startswith('AND2') and len(gate['endpoints'])==1
 ffpin=gate['endpoints'][0]['pin'];ff=next(r for r in rs if inst(r['driver'])==inst(ffpin));assert ff['role']=='ff'
 other=next((r,e) for r in rs for e in r['endpoints'] if inst(e['pin'])==inst(gatepin) and e['pin']!=gatepin)
 assert other[1]['inverted']==1,(port,other)
 if rnowner is None:rnowner=other[0]['driver']
 assert rnowner==other[0]['driver']
 # Original FF captures raw input. AND moves after the raw FF and retains every consumer/parity.
 consumers=ff['endpoints'];ff['endpoints']=[{'pin':gatepin,'inverted':0}];gate['endpoints']=consumers;raw['endpoints']=[{'pin':ffpin,'inverted':0}]
 other[0]['endpoints'].remove(other[1]);predicates.append({'port':port,'gate':gate['driver'],'raw_ff':ff['driver'],'sampled_rn_sink':other[1]['pin'],'consumer_count':len(consumers)})
rs.append({'driver':'MODEL_sampled_rn/QN','role':'ff','master':'DFFHQNx1_ASAP7_75t_R','endpoints':[{'pin':x['sampled_rn_sink'],'inverted':0} for x in predicates]})
roots[rnowner]['endpoints'].append({'pin':'MODEL_sampled_rn/D','inverted':1})
# Real resettable pin FFs. Keep the original 16 distinct local TIELOs as D sources.
# One dedicated real TIEHI drives their SETN (16 loads); inherited rn drives RESETN.
rs.append({'driver':'MODEL_pin_set_hi/H','role':'tie','master':'TIEHIx1_ASAP7_75t_R','endpoints':[]})
for bit in list(range(32,40))+list(range(48,56)):
 port='PORT/t_host['+str(bit)+']';tie,e=next((r,e) for r in rs for e in r['endpoints'] if e['pin']==port);assert tie['master'].startswith('TIELO') and e['inverted']==0
 name='MODEL_pin_zero_'+str(bit);e['pin']=name+'/D'
 rs.append({'driver':name+'/QN','role':'ff','master':'DFFASRHQNx1_ASAP7_75t_R','endpoints':[{'pin':port,'inverted':0}]})
 roots[rnowner]['endpoints'].append({'pin':name+'/RESETN','inverted':1})
 next(r for r in rs if r['driver']=='MODEL_pin_set_hi/H')['endpoints'].append({'pin':name+'/SETN','inverted':0})
by,copies,rounds=fixed(rs)
lef=pathlib.Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef');t=lef.read_text();sizes={}
for m in re.finditer(r'MACRO (\S+)\s+(.*?)END \1',t,re.S):
 q=re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',m[2]);
 if q:sizes[m[1]]=tuple(map(float,q.groups()))
assert all(r[0]['master'] in sizes for r in by.values())
geo={r['driver']:r for r in map(json.loads,gzip.open(P/'input/logical_roots.jsonl.gz','rt'))}
macros=json.load(open(P/'input/macros.json'));macropos={m['instance']:m for m in macros}
# Preserve old physical orientation for this deliberately conditional legacy geometry model.
# Top hx pair translated +86.4um; lower ox and sd pair stay at y43.2.
def external(pin):
 if pin.startswith('PORT/'):
  for g in geo.values():
   if g['driver']==pin:return g['source_xy_um']
   for e in g['endpoints']:
    if e['pin']==pin:return e['xy_um']
  raise AssertionError(pin)
 n=inst(pin)
 for g in geo.values():
  if g['driver']==pin:q=g['source_xy_um'];break
  match=next((e['xy_um'] for e in g['endpoints'] if e['pin']==pin),None)
  if match is not None:q=match;break
 else:raise AssertionError(pin)
 return [q[0],q[1]+(86.4 if '.g_hx_sram.' in n else 0)]
# Cache external centroids in one pass (avoid repeated whole graph scans).
extxy={}
for g in geo.values():
 if g['driver'].startswith('PORT/') or inst(g['driver']) in macropos:extxy[g['driver']]=g['source_xy_um']
 for e in g['endpoints']:
  if e['pin'].startswith('PORT/') or inst(e['pin']) in macropos:extxy[e['pin']]=e['xy_um']
for pin,q in extxy.items():
 if q is not None and '.g_hx_sram.' in pin:extxy[pin]=[q[0],q[1]+86.4]
# Every std-cell body, including incoming D/reset/set owners, is packed, not merely new copy points.
boundary=set()
for r in rs:
 for e in r['endpoints']:
  if r['role'] in ('input','macro') and inst(e['pin']) in by:boundary.add(inst(e['pin']))
  if e['pin'].startswith('PORT/') or inst(e['pin']) in macropos:
   if inst(r['driver']) in by:boundary.add(inst(r['driver']))
# 0.27um rows, 0.054um sites; each occupied rectangle includes one vacant site to its right.
# First reserve central finite slots for boundary-adjacent cells; fill other rows afterwards.
segments={i:[(0.,302.4)] for i in range(320)};placed={}
def place(n,k,central):
 w,h=sizes[by[n][0]['master']];assert abs(h-.27)<1e-8
 ww=math.ceil((w+0.054)/.054-1e-8)*.054
 rowrange=range(0,240) if central else range(320)
 for row in rowrange:
  for idx,(lo,hi) in enumerate(segments[row]):
   x=max(lo,75.6) if central else lo;end=min(hi,226.8) if central else hi
   if x+ww<=end+1e-8:
    placed[n,k]=[round(x,9),round(108+row*.27,9),w,h]
    pieces=[]
    if lo<x-1e-8:pieces.append((lo,x))
    if x+ww<hi-1e-8:pieces.append((x+ww,hi))
    segments[row][idx:idx+1]=pieces;return
 raise AssertionError(('no finite slot',n,k,central))
for central in (True,False):
 for n in sorted(by):
  if (n in boundary)!=central:continue
  for k in range(copies[n]):place(n,k,central)
# Use worst-case rectangle-corner L1 for both physical cells, exact frozen centroid for external pins.
def box(pin,k):
 n=inst(pin)
 if n in by:
  x,y,w,h=placed[n,k];return x,y,x+w,y+h
 q=extxy[pin];assert q is not None,pin
 return q[0],q[1],q[0],q[1]
def reach(a,b):return max(abs(a[0]-b[2]),abs(a[2]-b[0]))+max(abs(a[1]-b[3]),abs(a[3]-b[1]))
edges=[];far=[];maxr=0
for r in rs:
 n=inst(r['driver']);es=[(e,j) for e in r['endpoints'] for j in range(copies.get(inst(e['pin']),1))]
 # Explicit <=32 partitions for every output, including secondary roots on one physical master.
 for idx,(e,j) in enumerate(es):
  k=idx//32 if n in by else 0
  assert k<copies.get(n,1)
  v=reach(box(r['driver'],k),box(e['pin'],j));maxr=max(maxr,v)
  edges.append([r['driver'],k,e['pin'],j,e['inverted'],round(v,6)])
  if v>405+1e-8:far.append(edges[-1])
counts=collections.Counter();area=0
for n,rr in by.items():counts[rr[0]['role']]+=copies[n]-oldcopies.get(n,0);area+=(copies[n]-oldcopies.get(n,0))*masters[rr[0]['master']]['area_um2']
basearea=sum(masters[rr[0]['master']]['area_um2'] for rr in oldby.values());oldextra=sum((oldcopies[n]-1)*masters[rr[0]['master']]['area_um2'] for n,rr in oldby.items());mass=12391.76070+oldextra+area
out={'scope':'MODEL ONLY: finite logical-cell rectangle packing, no legal placement/physical/source qualification','source_commit':'3ebb699a9bd3564837e84e018e4c2c7c1e3cae8c','native_odb_sha256':d['odb_sha256'],'parent_binding':None,'parent_clock_phase':None,'macro_access_qualified':False,'original_all_output_fixedpoint':oldrounds,'boundary_revised_fixedpoint':rounds,'increment_beyond_236_625':dict(counts),'increment_area_um2':area,'total_std_mass_um2_including_old_transparent_cts':mass,'band_um':[0,108,302.4,194.4],'logical_cell_bodies':len(placed),'boundary_owner_instances':len(boundary),'all_expanded_root_edges':len(edges),'worst_rectangle_corner_L1_um':maxr,'over405':far,'unused_row_area_um2':sum(sum(hi-lo for lo,hi in seg)*.27 for seg in segments.values()),'legacy_nonlogical_mass_um2':12391.76070-basearea,'buffer_inv_cts_instance_count':100132-4-len(oldby),'buf_inv_cts_finite_geometry_proved':False,'native_LEF_sha256':hashlib.sha256(lef.read_bytes()).hexdigest(),'predicates':predicates,'rn_owner':rnowner,'new_data_edges_equational_component':0,'parent_schedule_age':None}
out['clock_increment_beyond_236_625_fF']={'TT':17*.462899+.474736,'FF':17*.503152+.522010}
out['legacy_missing_rectangle_capacity_bound']={'count':42833,'area_um2':12391.76070-basearea,'max_native_master_width_um':1.62,'height_um':.27,'one_site_padding_area_um2':42833*.054*.27,'dedicated_rows':54,'row_y0_um':179.82,'guaranteed_shelf_area_um2':54*(302.4-1.674)*.27,'logical_max_y_um':max(b[1]+b[3] for b in placed.values()),'actual_identity_orientation_clock_pin_routing_unproved':True}
assert out['legacy_missing_rectangle_capacity_bound']['logical_max_y_um']<179.82
assert out['legacy_missing_rectangle_capacity_bound']['area_um2']+out['legacy_missing_rectangle_capacity_bound']['one_site_padding_area_um2']<out['legacy_missing_rectangle_capacity_bound']['guaranteed_shelf_area_um2']
(H/'revised_graph.json.gz').write_bytes(gzip.compress(json.dumps(rs,separators=(',',':')).encode(),mtime=0))
(H/'model.json').write_text(json.dumps(out,indent=2)+'\n')
for name,data in [('placements.json.gz',[[n,k,b] for (n,k),b in placed.items()]),('assignments.json.gz',edges)]:
 (H/name).write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
print(json.dumps(out,indent=2));assert not far
print('PASS finite logical bodies and every expanded incoming/output corner bound <=405; physical qualification HOLD')

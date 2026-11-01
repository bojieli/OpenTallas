import importlib.util,json,pathlib,collections,math,copy,re,gzip,sys
spec=importlib.util.spec_from_file_location('stm_schema_fbd',sys.argv[1]);S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
B=pathlib.Path(__file__).resolve().parent.parent;O=B/'overlay';O.mkdir(exist_ok=True)
T=json.load(open(B/'source_type.json'));Q=json.load(gzip.open(B/'private_proposal_v2.json.gz'));X=json.load(open(B/'extra_pins.json'));C=json.load(gzip.open(O/'canonical_pack_5.95.json.gz'));W,H=311.04,613.44
N=copy.deepcopy(T);N['outline_um']=[W,H];windows=C['windows'];pins=[]
def xy(f,c,d=0):return [c if f in 'NS' else(d if f=='W' else W-d),c if f in 'EW' else(d if f=='S' else H-d)]
for p in C['pins']:
 x,y=xy(p['face'],p['q']);pins.append(dict(p,x=x,y=y,role='canonical_data'))
for bus in N['buses']:
 z=windows[bus['name']];bus['window_um']=z['window_um']
# Keep exact existing scalar shapes; select existing free canonical M7 tracks, no data-pin writer/holes.
io=(B/'io.tcl').read_text();shapes={}
for a,c,l,x,y,w,h in re.findall(r'place_pin -pin_name (?:\{([^}]+)\}|(\S+)) -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}',io):shapes[a or c]=[float(w),float(h)]
def scalarbus(n):
 for pre in ['fclk_in_','fclk_out_','cland_fstart_in_','cland_fstart_out_']:
  if n.startswith(pre):return n[len(pre):]
 return None
scalar=[]
for face in 'NSEW':
 used_data={round(p['q'],6) for p in C['pins'] if p['face']==face and p['layer']=='M7'}
 candidates=[round(.032+.064*k,6) for k in range(math.ceil((6.48-.032)/.064),math.floor(((W if face in 'NS' else H)-6.48-.032)/.064)+1) if round(.032+.064*k,6) not in used_data and (face in 'EW' or not S.pg_blocked('M7',.032+.064*k))]
 aa=[p for p in X if p['face']==face]
 # Data-coupled endpoints retain the actual matching bus; control endpoints keep explicit roles.
 for p in sorted(aa,key=lambda p:(windows.get(scalarbus(p['name']),{}).get('center',369),p['name'])):
  bus=scalarbus(p['name']);z=windows.get(bus)
  if z:
   want=z['center']+(-4.32 if p['name'].startswith('fclk') else 4.32)
  else:want={'arst_n':367.2,'start_i':369.36,'cland_up_ready':373.68,'cland_up_fault':375.84,'fclk_out_cland_up':371.52,'cland_rstart_out':306.72}[p['name']]
  size=shapes[p['name']]
  def legal(c):
   x,y=xy(face,c,2.656 if face in 'NS' else 2.144)
   for q in scalar:
    if q['layer']!='M7':continue
    a=q['pin_size_um'];
    if abs(x-q['x'])<(size[0]+a[0])/2+.032 and abs(y-q['y'])<(size[1]+a[1])/2+.032:return False
   return True
  c=min((c for c in candidates if legal(c)),key=lambda c:abs(c-want));x,y=xy(face,c,2.656 if face in 'NS' else 2.144)
  scalar.append(dict(p,x=x,y=y,role='canonical_free_track_scalar',paired_bus=bus,pin_size_um=size))
pins+=scalar
# Straps/start: unchanged native names and widths; existing M5 lattice phase retained.
for p in X:
 if p['face']=='INTERIOR' and p['layer']=='M5':pins.append(dict(p,x=round(p['x']-60.48,6),y=round(p['y']-367.2,6),role='constant_count_strap',pin_size_um=shapes[p['name']]))
p=next(p for p in X if p['name']=='cland_tstart_in');pins.append(dict(p,x=207.392,y=315.36,role='collector_start',pin_size_um=shapes[p['name']]))
pinmap={p['name']:p for p in pins}
for st in N.get('count_straps',[]):st['sites_um']=[[pinmap[st['name'] if st['width']==1 and st['name'] in pinmap else f"{st['name']}[{i}]"]['x'],pinmap[st['name'] if st['width']==1 and st['name'] in pinmap else f"{st['name']}[{i}]"]['y']] for i in range(st['width'])]
for h,m in zip(N['hard_cores'],Q['macros']):h['origin_um']=m['rect'][:2]
# Explicit endpoint GEOMETRY only. Advisory FF assignments are not consumed or converted to clock identities.
ck=N['clock'];ck['tap_mode']='explicit';clear=S.TAP_CLEAR_UM
boxes=list(S.placed_macro_boxes(N,halo=clear).values());taken=[];table=[]
sites=[(round(.032+8.64*i,6),round(.032+8.64*j,6)) for i in range(1,36) for j in range(1,71) if clear<=.032+8.64*i<=W-clear and clear<=.032+8.64*j<=H-clear];sites=[p for p in sites if not any(a<p[0]<c and b<p[1]<d for a,b,c,d in boxes)]
for name in ['clk']+['clk_t'+str(i) for i in range(1,76)]:
 want=Q['clock_assignments'][name]['pin_xy_um'];legal=[p for p in sites if not any(abs(p[0]-a)<clear-1e-8 and abs(p[1]-b)<clear-1e-8 for a,b in taken)];p=min(legal,key=lambda p:abs(p[0]-want[0])+abs(p[1]-want[1]));taken.append(p);table.append({'name':name,'kind':'glue','xy':list(p),'insertion_ps':250,'insertion_tol_ps':40})
ck['taps']=table;ck['tap_um']=table[0]['xy'];ck['sink_bins_file']='results/qc_stm_geometry_1131/overlay/native_sink_estimate.json'
# Do not change any source_clock_port/source_clock_tap, edge-clock waveform or latency metadata.
lc=ck['landing_contract'];newbands=Q['landing_bands_entire_cell_bbox_um']
for name,r in newbands.items():lc['bands'][name]['rect_um']=r
for p in lc['pins']:
 z=pinmap[p['name']];p['xy_um']=[z['x'],z['y']]
for e in ck.get('edge_clocks',[]):
 z=pinmap[e['port']];e['tap_um']=[z['x'],z['y']]
for z in lc.get('collector_local_sources',[]):
 z['band']=copy.deepcopy(lc['bands'][z['name']]);win=windows[z['name']];p=xy(win['face'],win['center']);z['xy_um']=p;z['pin_xy_um']=p
rt=Q['existing_collector_reset_geometry'];lc['collector_tree']['root']=rt['root'];pos={r['q']:r['xy'] for r in rt['relays']}
for r in lc['collector_tree']['relays']:r['xy']=pos[r['q']]
N['reset']['tap_um']=rt['root']
# Existing FT stage counts retained; only their planned coordinates/windows move.
free=[(17.28+8.64*i,17.28+10.8*j) for i in range(33) for j in range(54) if 17.28+8.64*i<W-17.28 and 17.28+10.8*j<H-17.28 and not any(a<17.28+8.64*i<c and b<17.28+10.8*j<d for a,b,c,d in boxes)]
def sample(path,f):
 ls=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])];d=sum(ls)*f
 for a,b,L in zip(path,path[1:],ls):
  if d<=L+1e-8:return [a[k]+(b[k]-a[k])*(d/L if L else 0) for k in (0,1)]
  d-=L
 return path[-1]
for z in N['ft_slots']:
 a=windows[z['name']+'_i'];b=windows[z['name']+'_o'];p=xy(a['face'],a['center'],12.96);q=xy(b['face'],b['center'],12.96);path=[p,[(p[0]+q[0])/2,p[1]],[(p[0]+q[0])/2,q[1]],q] if a['face'] in 'EW' and b['face'] in 'EW' else[p,[p[0],q[1]],q];z['in_layers']=a['layers'];z['out_layers']=b['layers'];z['in_window_um']=a['window_um'];z['out_window_um']=b['window_um'];z['regs_um']=[list(min(free,key=lambda p:abs(p[0]-v[0])+abs(p[1]-v[1]))) for v in [sample(path,i/z['stations']) for i in range(z['stations'])]]
for z in table:
 p=next(p for p in X if p['name']==z['name']);pins.append(dict(p,x=z['xy'][0],y=z['xy'][1],role='explicit_clock_geometry',pin_size_um=shapes[z['name']]))
# Native-count-based positions are explicitly estimated; they are not measured bins or qualified consumer identities.
bins=[[sum(z['estimated_consumer_bbox_um'][::2])/2,sum(z['estimated_consumer_bbox_um'][1::2])/2,z['actual_named_local_FF_count']] for z in Q['clock_assignments'].values()]
est={'n':52609,'bin_um':10.8,'bins':bins,'source':'ACTUAL_NATIVE_FF_COUNT_ESTIMATED_TARGET_GEOMETRY; NOT measured placement or qualified clock identity','type':'slw_stm_v3','qualified':False,'note':'Normal report adds its control sinks; no source offsets or tap wiring inferred from these bins.'};(O/'native_sink_estimate.json').write_text(json.dumps(est,indent=1)+'\n')
assert len(pins)==17874 and len(pinmap)+76==17874
# Field delta makes the exact private metadata changes reviewable; native ABI/timing/source fields remain untouched.
def diff(a,b,path=''):
 if type(a)!=type(b):return [path]
 if isinstance(a,dict):
  out=[]
  for k in a.keys()|b.keys():out+=([path+'/'+k] if k not in a or k not in b else diff(a[k],b[k],path+'/'+k))
  return out
 if isinstance(a,list):
  if len(a)!=len(b):return[path]
  return sum((diff(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
 return [] if a==b else[path]
(O/'type_overlay.json').write_text(json.dumps(N,indent=1)+'\n');(O/'named_pin_locations.json').write_text(json.dumps(pins,indent=1)+'\n');(O/'field_delta.json').write_text(json.dumps({'source':'d90b109213c6949da87b330ef143d96bbe937934','type':'slw_stm_v3','private_only':True,'changed_paths':diff(T,N),'unchanged_obligations':['all native RTL/13-source closure/netlist','module/buses widths/directions/layers/orders/leafs','76 clock ports','FT stage counts','collector/reset d/q connections/depths','source_clock_port/source_clock_tap/export forms','exact frozen per-port timing contracts'],'estimated_only':['sink positions/loads','clock-entry geometry','FT/reset target sites'],'CAD':'NOT RUN'},indent=2)+'\n')
def maxwin(v):
 v=sorted(v);a=0;m=0;example=None
 for i,x in enumerate(v):
  while x-v[a]>10+1e-8:a+=1
  if i-a+1>m:m=i-a+1;example=[v[a],x]
 return m,example
census=[]
for f in 'NSEW':
 for l in ['M4','M5','M6','M7']:
  ps=[p for p in pins if p['face']==f and p['layer']==l and p['role'] in ['canonical_data','canonical_free_track_scalar']]
  if ps:
   m,e=maxwin([p['x'] if f in 'NS' else p['y'] for p in ps]);census.append({'face':f,'layer':l,'count':len(ps),'peak10um':m,'interval_um':e,'status':'WARN budget>6/um/layer' if m>60 else'within budget'})
(O/'canonical_pin_census.json').write_text(json.dumps({'pins':17874,'canonical_data_pins':17671,'scalar_pins':203,'PG_keepouts_um':S.PART_PG_BANDS,'actual_data_ends_um':C['ends'],'density':census,'density_policy':'WARN budget pressure; actual pinaccess/DRC/GRT decide. No strict60 PASS claimed.','outline':[W,H],'nominal_std_free_fill':Q['std_fill_free_nominal'],'per_port_clock_contract':json.load(open(O/'frozen_clock_binding.json'))},indent=2)+'\n')
print('OVERLAY',O,'pins',len(pins),'changed_fields',len(diff(T,N)),'clock_ports',len(table),'density_peaks',[(x['face'],x['layer'],x['peak10um']) for x in census])

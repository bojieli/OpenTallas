import json,copy,math,re,collections,importlib.util,pathlib,gzip,bisect
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
O=pathlib.Path(__file__).resolve().parent
SRC=O/'source_types.json'
A=json.load(open(SRC)); spec=importlib.util.spec_from_file_location('S','/srv/opentallas-scratch/claude/wt/codex-bound-native-reset-1101/tools/die_plan/schema.py');S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
L={z['name']:z for z in S.ASAP7_LAYERS};areas=[32911.8714,32632.2999];names=['sle_stm_v1__cl27746664','sle_stm_v2__cl55be2264'];result={};full={}
def ceilgrid(x):return round(math.ceil((x-1e-8)/8.64)*8.64,6)
def peak(v):
 v=sorted(v);j=0;m=0;at=None
 for i,x in enumerate(v):
  while v[j]<x-10+1e-8:j+=1
  if i-j+1>m:m=i-j+1;at=[round(x-10,6),x]
 return {'pins_per_10um':m,'window_um':at,'over6_budget':m>60}
for n,area in zip(names,areas):
 t=A['types'][n];groups=[];native=[]
 for b in t['buses']:
  groups.append(dict(name=b['name'],face=b['face'],width=b['width']+1,layers=b['layers'],order=b.get('order','lsb_low'),old=b['window_um'][0]))
 for b in t['ft_slots']:
  for side in ['in','out']:
   w=b.get(side+'_window_um')
   if w is None:
    # Input slot is not a buses row. Original pins give its exact order on the face.
    w=[0,0]
   groups.append(dict(name=b['name']+('_i' if side=='in' else '_o'),face=b[side+'_face'],width=b['width']+1,layers=b['layers'],order=b.get('order','lsb_low'),old=w[0]))
 text=gzip.open(O/(n+'_native_io.tcl.gz'),'rt').read()
 for m in re.finditer(r'place_pin -pin_name (?:\{([^}]+)\}|(\S+)) -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}',text):
  name=m[1] or m[2];ln=m[3];x,y,w,h=map(float,m.group(4,5,6,7));f='W' if x<3 else 'E' if x>610 else 'S' if y<3 else 'N' if y>1336 else 'INTERIOR';native.append(dict(name=name,layer=ln,x=x,y=y,face=f,size=[w,h]))
 data={f"{g['name']}[{i}]" for g in groups for i in range(g['width'])};actualnames={p['name'] for p in native};missing=data-actualnames
 # Scalar width-1 buses may use scalar native spelling. Preserve that explicit identity.
 for g in groups:
  if g['width']==1 and g['name'] in actualnames:data.discard(g['name']+'[0]');data.add(g['name'])
 assert not(data-actualnames),(n,len(data-actualnames),list(data-actualnames)[:3])
 aux=[p for p in native if p['name'] not in data]
 for g in groups:
  hits=[p for p in native if p['name']==g['name'] or p['name'].startswith(g['name']+'[')]
  assert len(hits)==g['width'],(g,len(hits))
  g['old']=min(p['x'] if g['face'] in 'NS' else p['y'] for p in hits)
 rows=[];models=[]
 for rate in [5.95,6.0,6.1,6.25,6.3,6.5,6.75,7.0]:
  ends={};pins=[];windows=[]
  for face in 'NSEW':
   pos=6.48
   for g in sorted([z for z in groups if z['face']==face],key=lambda z:(z['old'],z['name'])):
    counts=[len(range(i,g['width'],len(g['layers']))) for i in range(len(g['layers']))]
    span=max(counts)/rate+.128;hi=pos+span
    p={'id':g['name'],'width':g['width'],'epoch':False,'layers':g['layers'],'window_um':[round(pos,6),round(hi,6)],'order':g['order']}
    while True:
     try: pp=S.pin_positions(p,L);break
     except ValueError:
      hi+=.016;p['window_um'][1]=round(hi,6)
    pins += [dict(name=f"{g['name']}[{b}]",layer=ln,q=q,face=face,role='data') for b,ln,q in pp]
    windows.append(dict(g,window_um=p['window_um']));pos=hi+.96
   ends[face]=round(pos-.96,6)
  W=ceilgrid(max(ends['N'],ends['S'])+6.48);H=ceilgrid(max(ends['E'],ends['W'])+6.48)
  W=max(W,ceilgrid(H/2),302.4);H=max(H,ceilgrid(W/2));core=(W-8.64)*(H-8.64);macro=4*121.848*62.952
  scalars=[];failure=[]
  for p in aux:
   f=p['face'];ln=p['layer']
   if f=='INTERIOR':continue
   limit=W if f in 'NS' else H;oldlim=613.44 if f in 'NS' else 1339.2;wanted=(p['x'] if f in 'NS' else p['y'])/oldlim*limit
   v=L[ln];k0=math.ceil((6.48-v['offset_um'])/v['pitch_um']);k1=math.floor((limit-6.48-v['offset_um'])/v['pitch_um'])
   used=sorted(z['q'] for z in pins if z['face']==f and z['layer']==ln)
   prior=[z for z in scalars if z['face']==f and z['layer']==ln]
   clearance=(p['size'][0] if f in 'NS' else p['size'][1])/2+.032
   options=[round(v['offset_um']+k*v['pitch_um'],6) for k in range(k0,k1+1) if not S.pg_blocked(ln,v['offset_um']+k*v['pitch_um'])]
   def free(q):
    i=bisect.bisect_left(used,q)
    return all(abs(q-z)>=clearance+.016 for z in used[max(0,i-1):i+1]) and all(abs(q-z['q'])>=clearance+z['half_size'] for z in prior)
   options=[q for q in options if free(q)]
   if not options:failure.append(p['name']);continue
   q=min(options,key=lambda q:abs(q-wanted));scalars.append(dict(name=p['name'],layer=ln,face=f,q=q,role='scalar',half_size=clearance-.032))
  density={f+'-'+ln:peak([p['q'] for p in pins+scalars if p['face']==f and p['layer']==ln]) for f in 'NSEW' for ln in ['M4','M5','M6','M7'] if any(p['face']==f and p['layer']==ln for p in pins+scalars)}
  row={'target_pins_per_um_per_layer':rate,'outline_um':[W,H],'aspect':round(max(W/H,H/W),6),'core_inset_um':4.32,'core_area_um2':core,'macro_area_um2':macro,'native_regular_std_area_um2':area,'std_fill_free':area/(core-macro),'data_ends_um':ends,'last_legal_um':{'N':W-6.48,'S':W-6.48,'W':H-6.48,'E':H-6.48},'scalar_edge_allocated':len(scalars),'scalar_edge_failures':failure,'density':density,'max_10um_count':max(z['pins_per_10um'] for z in density.values()),'meets_fill20_aspect2':area/(core-macro)>=.2 and max(W/H,H/W)<=2,'PG_clear':all(not S.pg_blocked(z['layer'],z['q']) for z in pins+scalars),'not_qualified':['native scalar face/inset preserved only as planning contact allocation','interior auxiliary placement pending','clock homes/source/timing unchanged and not geometrically qualified','macro escape/consumer windows/nonFF regional allocation and parent peer context pending','actual placement/pin access/PG/DRC/GRT/timing not run']}
  rows.append(row);models.append({'summary':row,'windows':windows,'data_pins':pins,'scalar_pins':scalars})
 census={'all_native_contacts':len(native),'data_contacts':len(data),'data_per_face':dict(collections.Counter(g['face'] for g in [])),'aux_contacts':len(aux),'aux_edge_per_face_layer':dict(collections.Counter(p['face']+'-'+p['layer'] for p in aux)),'native_clock_ports':len([p for p in aux if p['name']=='clk' or re.fullmatch(r'clk_t\d+',p['name'])]),'native_clock_names':[p['name'] for p in aux if p['name']=='clk' or re.fullmatch(r'clk_t\d+',p['name'])],'frozen_clock_metadata_records':len(t['clock']['taps']),'edge_clocks':len(t['clock'].get('edge_clocks',[])),'native_interior_aux_names':[p['name'] for p in aux if p['face']=='INTERIOR' and not (p['name']=='clk' or re.fullmatch(r'clk_t\d+',p['name']))],'source':'exact old5346 native io.tcl; closure source-normalized-match to d90, geometry NOT adopted'}
 census['data_per_face']={f:sum(g['width'] for g in groups if g['face']==f) for f in 'NSEW'}
 result[n]={'census':census,'frontier':rows};full[n]=models
(O/'frontier.json').write_text(json.dumps({'scope':'PRIVATE source-only pin/area tradeoffs; no GEN/CAD/clock qualification/source adoption','source':A['source'],'types':result,'standard_PG_bands':S.PART_PG_BANDS,'edge_guards_um':{'core_rim':4.32,'both_end_extra':2.16,'inter_bundle_gap':.96},'density_policy':'6/um/layer is WARN budget; exact sliding10um values disclosed, not a hard P&R prohibition','macro_layout':'2x2 relative spacing155.52x95.04 retained; candidate footprint277.368x157.992 plus4.32halo; schematic origin snapped4.32 and y+.012; consumer/escape still held'},indent=2)+'\n')
with gzip.open(O/'canonical_candidate_contacts.json.gz','wt') as f:json.dump(full,f)
fig,axes=plt.subplots(1,2,figsize=(11,7))
for ax,n in zip(axes,names):
 models=full[n];chosen=next((m for m in models if m['summary']['meets_fill20_aspect2']),models[-1]);r=chosen['summary'];W,H=r['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2));ax.add_patch(Rectangle((4.32,4.32),W-8.64,H-8.64,fill=False,ls='--',color='grey'))
 for i in range(4):
  x=round((W-277.368)/2/4.32)*4.32+(i%2)*155.52;y=round((H-158)/2/4.32)*4.32+.012+(i//2)*95.04;ax.add_patch(Rectangle((x-4.32,y-4.32),130.488,71.592,fc='#f7dfbb',ec='orange',alpha=.7));ax.add_patch(Rectangle((x,y),121.848,62.952,fc='#cfdbed',ec='navy'))
 colors={'M4':'#397c44','M5':'#7451a6','M6':'#bf3030','M7':'#187b9c'}
 for p in chosen['data_pins']+chosen['scalar_pins']:
  f=p['face'];q=p['q'];x,y=(q,H if f=='N' else 0) if f in 'NS' else (W if f=='E' else 0,q);ax.plot(x,y,'.',ms=.7,color=colors[p['layer']])
 ax.set(xlim=(-15,W+15),ylim=(-15,H+15),aspect='equal',xlabel='um',ylabel='um',title=f"{n}\n{W}×{H} um; free fill {r['std_fill_free']:.2%}\npeak {r['max_10um_count']}/10um/layer WARN")
 ax.text(W/2,H*.14,'PRIVATE AREA / PIN TRADEOFF\nNo clock/source or physical qualification\nInterior aux / consumer locality / PG escape held',ha='center',fontsize=7)
fig.tight_layout();fig.savefig(O/'sle_frontier.png',dpi=150)
for n,r in result.items():print(n,r['census']);print([(x['outline_um'],round(x['std_fill_free'],5),x['max_10um_count'],len(x['scalar_edge_failures'])) for x in r['frontier']])

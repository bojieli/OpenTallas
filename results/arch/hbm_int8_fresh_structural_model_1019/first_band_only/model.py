"""Finite analytical native-source layout MODEL. No RTL/netlist/ODB writes or engine.
Bounding-box cell centers are a routing proxy, never native contact/extracted RC.
"""
import pathlib,json,gzip,sys,math,hashlib,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
P=pathlib.Path(__file__).parent;K=P/'kit';sys.path.insert(0,str(K))
from dft.liberty import read_liberty
from lib_native import blocks,scalar
load=lambda n:json.load(gzip.open(K/'inputs'/(n+'.json.gz'),'rt'))
B=load('positions');R=load('raw');A=json.load(open(K/'allowlist.json'))
M=next(iter(R['modules'].values()));C=M['cells'];CL=json.load(open(K/'inputs/clock_cost.json'))
clock={r['instance']:r for r in CL['rows']};removed={n for n,r in clock.items() if not r['open_output_clock_load']}
L={c:read_liberty(sorted((K/'inputs/native_libs').glob('*'+c+'*'))) for c in ('TT','FF')}
masters={n:c['type'] for n,c in C.items() if n not in removed}
for n,r in A['replacement_cells'].items():masters[n]=r['new_master']
masters.update({n:r['master'] for n,r in A['added_cells'].items()})
newclock={f'MODEL_clock_l{lev}_{i}':'BUFx24_ASAP7_75t_R' for lev,count in [(0,1),(1,16),(2,128)] for i in range(count)}
masters.update(newclock)
assert len(removed)==143 and len(newclock)==145 and len(masters)==12491
# Widths are exact native frozen bboxes; height .27 and site .054 um.
width={r['master']:(r['bbox'][2]-r['bbox'][0])/1000 for r in B['insts'].values()}
width.update({r['master']:(r['bbox'][2]-r['bbox'][0])/1000 for r in A['placement'].values()})
area=sum(L['TT'][m]['area'] for m in masters.values())
assert abs(area-1668.41856)<1e-5,(area,)
# Fresh placements have no old FIRM origins or orientation obligation. Existing
# source geometry seeds 16 connectivity cohorts; additions inherit actual sink.
anchor={n:((r['bbox'][0]+r['bbox'][2])/2000,(r['bbox'][1]+r['bbox'][3])/2000) for n,r in B['insts'].items()}
for br in A['branches']:
    sinks=[anchor[s['cell']] for s in br['sinks']]
    q=(sum(x for x,y in sinks)/len(sinks),sum(y for x,y in sinks)/len(sinks))
    for n in br['buffers']:anchor[n]=q
    if br.get('inverter') not in (None,*anchor.keys()):anchor[br['inverter']]=q
signal=[n for n in masters if n not in newclock]
signal.sort(key=lambda n:(anchor[n][0],anchor[n][1],n))
cohorts=[[] for _ in range(16)];acc=0;signal_area=sum(L['TT'][masters[n]]['area'] for n in signal)
for n in signal:
    i=min(15,int(16*(acc+L['TT'][masters[n]]['area']/2)/signal_area));cohorts[i].append(n);acc+=L['TT'][masters[n]]['area']
for i in range(16):
    cohorts[i].append(f'MODEL_clock_l1_{i}')
    cohorts[i]+=[f'MODEL_clock_l2_{i*8+j}' for j in range(8)]
cohorts[8].append('MODEL_clock_l0_0')
# 68 existing .27-um row heights, 216-um full-width band. A .108-um
# inter-cohort corridor and .054-um exterior guards are actual priced whitespace.
X0,Y0,W,H=10.8,55.62,216.,18.36
boxes={};cohort_report=[]
for ci,names in enumerate(cohorts):
    names.sort(key=lambda n:(anchor.get(n,(0,64.8))[1],n))
    rows=[[] for _ in range(68)];total=sum(width[masters[n]] for n in names);s=0
    for n in names:
        ri=min(67,int(68*(s+width[masters[n]]/2)/total));rows[ri].append(n);s+=width[masters[n]]
    maxfill=0
    for ri,ns in enumerate(rows):
        widths=sum(width[masters[n]] for n in ns);span=13.5-.108
        assert widths<=span,(ci,ri,widths)
        maxfill=max(maxfill,widths/span)
        gap=(span-widths)/(len(ns)+1);x=X0+ci*13.5+.054+gap
        for n in ns:
            w=width[masters[n]];y=Y0+.27*ri;boxes[n]=[x,y,x+w,y+.27];x+=w+gap
    ca=sum(L['TT'][masters[n]]['area'] for n in names)
    cohort_report.append(dict(cohort=ci,cells=len(names),area_um2=ca,utilization=ca/(13.5*H),max_row_fill=maxfill))
assert len(boxes)==len(masters)
center={n:((b[0]+b[2])/2,(b[1]+b[3])/2) for n,b in boxes.items()}
# Exact virtual signal graph for demand measurement, excluding all old clock
# infrastructure (its 110 unary loads remain real sinks in fresh clock model).
connections={n:{p:list(v) for p,v in c['connections'].items()} for n,c in C.items() if n not in clock}
ids={r['name']:int(k) for k,r in M['net_metadata'].items()};nextid=max(ids.values())+1
for name in A['added_nets']:ids[name]=nextid;nextid+=1
for n in A['added_cells']:connections[n]={}
for r in A['rewired_pins']:connections[r['cell']][r['pin']]=[ids[r['new_net']]]
pts=collections.defaultdict(list)
for n,pins in connections.items():
    for p,bits in pins.items():
        if p in ('VDD','VSS','CLK'):continue
        for bit in bits:pts[bit].append(center[n])
for name,port in M['ports'].items():
    if name in ('clk','VDD','VSS'):continue
    pin=B['bterms'].get(name,[])
    xy=[((b[1]+b[3])/2000,(b[2]+b[4])/2000) for q in pin for b in q['boxes']]
    for bit in port['bits']:pts[bit]+=xy
netrows=[]
for bit,xy in pts.items():
    if len(xy)<2:continue
    xs,ys=zip(*xy);bb=[min(xs),min(ys),max(xs),max(ys)]
    netrows.append(dict(bit=bit,bbox=bb,center_hpwl_um=bb[2]-bb[0]+bb[3]-bb[1],contacts=len(xy)))
cutx=[dict(x_um=X0+13.5*i,demand=sum(r['bbox'][0]<X0+13.5*i<r['bbox'][2] for r in netrows)) for i in range(1,16)]
cuty=[dict(y_um=Y0+H*i/16,demand=sum(r['bbox'][1]<Y0+H*i/16<r['bbox'][3] for r in netrows)) for i in range(1,16)]
# Fresh clock load count and native pin caps, no source-name exemptions.
ff=[n for n,m in masters.items() if L['TT'][m]['ff']];openloads=[n for n,r in clock.items() if r['open_output_clock_load']]
leaves=[[] for _ in range(128)]
for i,n in enumerate(sorted(ff+openloads,key=lambda n:center[n])):leaves[min(127,i*128//len(ff+openloads))].append(n)
caps={}
for corner in ('TT','FF'):
    nativecaps={}
    for path in sorted((K/'inputs/native_libs').glob('*'+corner+'*')):
        text=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
        for master,body in blocks(text,'cell'):
            nativecaps[master]={pin:scalar(pb,'capacitance') for pin,pb in blocks(body,'pin')}
    def cap(m,p):
        value=nativecaps[m][p];assert value is not None,(m,p);return value
    leafcaps=[]
    for ns in leaves:
        leafcaps.append(sum(cap(masters[n],next(p for p,r in L[corner][masters[n]]['pins'].items() if r['clock'])) if n in ff else cap(masters[n],'A') for n in ns))
    caps[corner]=dict(all_real_sink_clock_pin_cap_fF=sum(leafcaps),max_leaf_pin_cap_fF=max(leafcaps),
        region_eight_buffer_pin_cap_fF=8*cap('BUFx24_ASAP7_75t_R','A'),
        root_sixteen_buffer_pin_cap_fF=16*cap('BUFx24_ASAP7_75t_R','A'),wire_cap_fF=None,qualified=False)
result=dict(schema='int8.fresh_source_structural_model.v1',status='MODEL_ONLY_CAPACITY_TIMING_HOLD',
    source_checkpoint_sha256=R['source_odb_sha256'],outline_um=[237.6,129.6],band_um=[X0,Y0,W,H],
    original_rows_preserved=464,source_cells=10623,replacements=1078,additions=1866,removed_old_clock=143,
    fresh_clock_buffers=145,retained_genuine_open_clock_loads=110,all_cells=len(masters),ff=len(ff),
    area_um2=area,increment_over_original_um2=area-1398.39696,band_utilization=area/(W*H),
    native_pg_terminals=2*len(masters),fresh_clock=dict(levels=[1,16,128],functional_buffers_area_um2=145*.4374,
    retained_open_load_area_um2=13.31154,all_clock_area_um2=145*.4374+13.31154,
    real_sink_count=len(ff+openloads),leaf_max_loads=max(map(len,leaves)),regional_max_loads=8,root_max_loads=16,
    early_late_arrival_ps=None,TT_spread_ps=None,FF_spread_ps=None,native_pin_caps=caps,qualified=False),
    ownership=dict(D_hold=594,RESETN_hold=10,hold_cells=1812,reset_split_branches=12,new_state=0,new_architectural_edges=0),
    geometry=dict(kind='fresh deterministic source-cohort packed boxes; no legalizer/native contact claim',
    cohorts=cohort_report,all_net_center_HPWL_um=sum(r['center_hpwl_um'] for r in netrows),
    max_net_center_HPWL_um=max(r['center_hpwl_um'] for r in netrows),x_cuts=cutx,y_cuts=cuty,
    native_track_capacity=dict(M2_band_gross_optimistic=68*7,M4_band_gross=382,M6_band_gross=287,
        M2_M4_band_gross_optimistic=858,M2_M4_M6_band_gross_optimistic=1145,
        M3_band_gross=6000,M5_band_gross=4500,M7_band_gross=3375,
        note='Native make_tracks pitches. M2 optimistic seven offset sets; no PG/clock/via/contact obstruction deduction. Full outline exterior belts not allocated.'),
    PG_track_occupancy=None,signal_route_cut_verdict='HOLD_GROSS_CAPACITY_ONLY_NO_PG_CLOCK_TRACK_BINDING'),
    obligations=dict(source_functions='same native source and exact identity hold/split mechanism; no new implementation',
    all_driver_census='required fresh complete native graph with BUF/INV transparent <=32',
    timing='fresh complete TT/FF D/async min/max, native waveform/table domain, SS setup required for qualification',
    small_load='292 TT source lower-wire-cap predicates remain OPEN; no distance-cap conversion',
    feedback='all seven boundary-feedback source conditions remain OPEN; IO80fF unchanged',
    nativePG='all24982 PG terms, birth binding, conductor/via/contact/short proof OPEN',
    pin_access='original full-face .192um pin geometry unchanged, actual access/PG interaction OPEN',
    clock='whole fresh tree waveform/cap/actualRC/pulse/spread OPEN, no old253 phase inheritance',
    parent='neighbour/root IO reference and token composition OPEN'))
(P/'model.json').write_text(json.dumps(result,indent=2)+'\n')
with gzip.open(P/'MODEL_boxes.json.gz','wt') as f:json.dump(dict(cells={n:dict(master=masters[n],bbox=b) for n,b in boxes.items()},leaves=leaves),f)
fig,ax=plt.subplots(figsize=(15,9));groups=collections.defaultdict(list)
for n,b in boxes.items():
    key='fresh clock' if n in newclock else 'retained clock load' if n in clock else 'FF' if n in ff else 'hold/addition' if n in A['added_cells'] else 'native signal'
    groups[key].append(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1]))
colors={'fresh clock':'#b13bad','retained clock load':'#713574','FF':'#3179b4','hold/addition':'#2c9c65','native signal':'#d89d30'}
for k,rs in groups.items():ax.add_collection(PatchCollection(rs,facecolor=colors[k],edgecolor='none'))
for ps in B['bterms'].values():
    for q in ps:
        for b in q['boxes']:ax.add_patch(Rectangle((b[1]/1000,b[2]/1000),max(.1,(b[3]-b[1])/1000),max(.1,(b[4]-b[2])/1000),color='#202020'))
ax.add_patch(Rectangle((X0,Y0),W,H,fill=False,edgecolor='black',lw=.8));ax.set(xlim=(0,237.6),ylim=(0,129.6),xlabel='um',ylabel='um',aspect='equal',title='INT8 fresh native-source structural MODEL — NO source implementation or engine\n12491 cells; all 2782 FF movable; 604 owned hold branches; fresh 145-buffer clock + 110 genuine loads')
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],marker='s',linestyle='',color=colors[k],label=f'{k}: {len(v)}') for k,v in groups.items()],fontsize=8)
fig.text(.09,.03,f'216 × 18.36 um central standard-cell band; native area {area:.5f} um² ({100*area/(W*H):.2f}% band). All 464 original rows / IO80fF retained.\nMODEL ONLY: native track/PG capacity, 292 source minimum-wire-cap predicates, feedback, fresh clock phase and full timing remain HOLD.',fontsize=9)
fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(P/'MODEL.png',dpi=180)
print(json.dumps({k:result[k] for k in ('status','all_cells','area_um2','band_utilization','native_pg_terminals','fresh_clock','geometry')},indent=2))

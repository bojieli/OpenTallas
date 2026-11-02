from pathlib import Path
import json,re,math
P=Path('/home/ubuntu/coord/tmp/codex-caprt-0148');src=json.load(open(P/'west_actual_DEF.json'));pg=json.load(open(P/'west_actual_PG.json'));assert pg['unknown_count']==0;dims={}
for l in Path('/home/ubuntu/coord/tmp/caprt1131/BclassF_final_geom.tsv').open():
 a=l.rstrip().split('\t')
 if a[0]=='C':dims[a[3]]=[round(float(a[6])-float(a[4]),6),round(float(a[7])-float(a[5]),6)]
dims.update({r['name']:r['size_um'] for r in json.load(open(P/'physical_master_dims.json'))});assert not {r['master'] for r in src['region_instances'] if r['master'] not in dims}
rows=[]
for s in src['rows']:
 a=s.split();rows.append(dict(x=int(a[3])/1000,y=int(a[4])/1000,orient=a[5],n=int(a[7]),step=int(a[11])/1000))
# Actual kit MACRO_PLACE_HALO and MACRO_ROWS_HALO_X/Y are4.32; same macro and PG as actual finalDEF.
macro=[38.88,38.88,221.64,77.256];power=[[r['rect_um'][0]-.096,r['rect_um'][1]-.096,r['rect_um'][2]+.096,r['rect_um'][3]+.096,'PG:'+r['kind']] for r in pg['region_pg_shapes']]
def intersects(a,b):return a[0]<b[2]-1e-6 and a[2]>b[0]+1e-6 and a[1]<b[3]-1e-6 and a[3]>b[1]+1e-6
def build(size=False):
 owned={'_27646_','wire17963'}|({'_27644_','_27645_'} if size else set());obs=[macro+['actual_macro_halo']]+power
 for r in src['region_instances']:
  if r['name'] in owned or r['master'].startswith('DECAP'):continue
  w,h=dims[r['master']];obs.append([r['x'],r['y'],r['x']+w,r['y']+h,r['name']])
 changes={}
 def place(name,preferred,region,master=None):
  old=src['targets'][name];master=master or old['master'];w,h=dims[master];cand=[]
  for row in rows:
   b=row['y']
   if not region[1]<=b<=region[3]-h:continue
   near=[q for q in obs if b<q[3]-1e-6 and b+h>q[1]+1e-6]
   lo=max(0,math.ceil((region[0]-row['x'])/row['step']));hi=min(row['n']-1,math.floor((region[2]-w-row['x'])/row['step']))
   for ix in range(lo,hi+1):
    a=round(row['x']+ix*row['step'],6)
    if a+w>row['x']+row['n']*row['step']+1e-6:continue
    box=[a,b,a+w,b+h]
    if any(intersects(box,q) for q in near):continue
    cand.append((abs(a-preferred[0])+abs(b-preferred[1]),a,b,row['orient'],box))
  assert cand,name
  q=min(cand);r=dict(master=master,origin_um=list(q[1:3]),orient=q[3],bbox_um=q[4],old=old);changes[name]=r;obs.append(q[4]+[name]);return r
 place('_27646_',(37.8,55.08),[29,38.88,38.88,72.9]);place('wire17963',(37.8,78.3),[29,77.256,41.2,86])
 if size:
  place('_27644_',(99.036,37.26),[97,35.64,101,38.34],'INVx2_ASAP7_75t_R');place('_27645_',(98.766,37.8),[97,35.64,101,38.34],'NAND2x2_ASAP7_75t_R')
 return changes
old={n:[r['x'],r['y']] for n,r in src['targets'].items()}
def corridor(a,b):
 # Macro halo orthogonal shortest path; no distance-to-delay or postmove slack inference.
 if not ((a[1]<38.88 and b[1]>77.256) or (b[1]<38.88 and a[1]>77.256)) or not (38.88<a[0]<221.64 and 38.88<b[0]<221.64):return abs(a[0]-b[0])+abs(a[1]-b[1])
 return min(abs(a[0]-38)+abs(b[0]-38),abs(a[0]-222.5)+abs(b[0]-222.5))+abs(a[1]-b[1])
actual=json.load(open(P/'actual_four_input_pricing.json'));opts=[]
for size in [False,True]:
 ch=build(size);xy=dict(old);xy.update({n:r['origin_um'] for n,r in ch.items()});prices=[]
 for pin,drv in {'A1':'wire19289','A2':'_27644_','B':'_27645_','C':'wire19399'}.items():prices.append(dict(pin=pin,driver=drv,old_corridor_um=round(corridor(old[drv],old['_27646_']),3),new_corridor_um=round(corridor(xy[drv],xy['_27646_']),3),actual_TT_input_arrival_ps=actual['arrivals']['tt'][pin]['max']['arrival_ps']['_27646_/'+pin],actual_TT_receiver_setup_ps=actual['arrivals']['tt'][pin]['max']['slack_ps'],actual_FF_receiver_hold_ps=actual['arrivals']['ff'][pin]['min']['slack_ps']))
 opts.append(dict(id='WEST4_SIZE2' if size else 'WEST2_MOVE_ONLY',changes=ch,input_prices=prices,output_chain_old_um=round(corridor(old['_27646_'],old['wire17963'])+corridor(old['wire17963'],old['lweco_219418']),3),output_chain_new_um=round(corridor(xy['_27646_'],xy['wire17963'])+corridor(xy['wire17963'],xy['lweco_219418']),3),signal_dirty_netset=['net19290','_14198_','_14199_','net19400','_14200_','net17964']+(['ga_key[7][19]','ga_key[3][19]'] if size else []),extra_area_um2=round(sum(dims[v['master']][0]*dims[v['master']][1]-dims[v['old']['master']][0]*dims[v['old']['master']][1] for v in ch.values()),6),postmove_slack='NOT_PREDICTED; native exactTT/FF required afterROOT approved event',actual_cell_count_unchanged=True))
result=dict(schema='opentallas.caprt_balanced_west_prep.v1',verdict='PREP_ONLY_NO_CANDIDATE_CAD',options=opts,source_DEF_sha256=pg['source_sha256'],native_input_pricing_units=actual['units'],actual_rows=len(rows),region_cells=len(src['region_instances']),PG_shapes=len(pg['region_pg_shapes']),PG_envelope='actual DEF paths/widths+explicitVIAS RECT; stripe endpoints conservative, extra0.096umkeepout',standard_spacer_removal='only actual LEF CLASS CORE SPACER DECAP; allTAP/functional/clock/FF untouched',scope='2existingmoves orsame2moves+2existingINV/NANDstrengthx2; no extra cells/RTL/reset/clock/cycles; all non-owned poses/masters/connectivity preserved',risk='West reduces C/output excursion while still lengthening A2/B; measured37ps TT headroom does not prove either option passes. Sized option changes input capacitance/upstream load and needs full timing, PG-swap/nativeaccess safeguards and routeLEC. No blanket buffers.')
(P/'balanced_west_options.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))

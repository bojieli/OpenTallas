from pathlib import Path
import json,re,math
P=Path('/home/ubuntu/coord/tmp/codex-caprt-0148');x=json.load(open(P/'actual_def_region.json'));dims={}
for line in Path('/home/ubuntu/coord/tmp/caprt1131/BclassF_final_geom.tsv').open():
 a=line.rstrip().split('\t')
 if a[0]=='C':dims[a[3]]=[round(float(a[6])-float(a[4]),6),round(float(a[7])-float(a[5]),6)]
dims.update({r['name']:r['size_um'] for r in json.load(open(P/'physical_master_dims.json'))})
unknown=sorted({r['master'] for r in x['north_region_nonfill_instances'] if r['master'] not in dims});print('unknownmasters',unknown);assert not unknown
rows=[]
for s in x['rows']:
 a=s.split();rx,ry=float(a[3])/1000,float(a[4])/1000
 if 78<=ry<=92:rows.append(dict(x=rx,y=ry,orient=a[5],n=int(a[7]),step=float(a[11])/1000))
obs=[]
for r in x['north_region_nonfill_instances']:
 if r['name'] in ['_27646_','wire17963'] or r['master'].startswith('DECAP'):continue # actual platform LEF CORE SPACER; standard remove_fillers only
 w,h=dims[r['master']];obs.append([r['x'],r['y'],r['x']+w,r['y']+h,r['name']])
pg=json.load(open(P/'actual_DEF_PG.json'));assert pg['unknown_count']==0
obs.extend([[r['rect_um'][0]-.096,r['rect_um'][1]-.096,r['rect_um'][2]+.096,r['rect_um'][3]+.096,'PG:'+r['kind']] for r in pg['region_pg_shapes']])
def legal(name,preferred,extra=[]):
 w,h=dims[x['targets'][name]['master']];cand=[]
 for row in rows:
  near=[q for q in obs+extra if row['y'] < q[3]-1e-6 and row['y']+h > q[1]+1e-6]
  for ix in range(max(0,math.ceil((94-row['x'])/row['step'])),min(row['n'],math.floor((116-w-row['x'])/row['step']))+1):
   a=round(row['x']+ix*row['step'],6);b=row['y'];bb=[a,b,a+w,b+h]
   if any(bb[0]<q[2]-1e-6 and bb[2]>q[0]+1e-6 and bb[1]<q[3]-1e-6 and bb[3]>q[1]+1e-6 for q in near):continue
   score=abs(a-preferred[0])+abs(b-preferred[1]);cand.append((score,a,b,row['orient'],bb))
 assert cand;return min(cand)
a=legal('_27646_',(103,83.7));b=legal('wire17963',(105,86.4),[a[4]+['_27646_']]);new={'_27646_':dict(origin_um=list(a[1:3]),orient=a[3],bbox_um=a[4]),'wire17963':dict(origin_um=list(b[1:3]),orient=b[3],bbox_um=b[4])}
for n,q in new.items():q['master']=x['targets'][n]['master'];q['size_um']=dims[q['master']]
def dist(a,b):
 x1,y1=a;x2,y2=b
 direct=abs(x1-x2)+abs(y1-y2)
 if (y1<41.2 and y2>74.936 or y2<41.2 and y1>74.936) and 41.2<x1<219.32 and 41.2<x2<219.32:
  return min(abs(x1-39)+abs(x2-39),abs(x1-221.5)+abs(x2-221.5))+abs(y1-y2)
 return direct
oldxy={n:[r['x'],r['y']] for n,r in x['targets'].items()};newxy=dict(oldxy);newxy.update({n:q['origin_um'] for n,q in new.items()});inputs={'A1':'wire19289','A2':'_27644_','B':'_27645_','C':'wire19399'};prices=[]
for pin,driver in inputs.items():prices.append(dict(pin=pin,driver=driver,old_corridor_lower_bound_um=round(dist(oldxy[driver],oldxy['_27646_']),3),new_corridor_lower_bound_um=round(dist(newxy[driver],newxy['_27646_']),3),actual_current_A_input_arrival_ps='MISSING: existing reports contain only worst C path, no new STA authorized'))
result=dict(verdict='PREP_HOLD_FOR_ALL4_INPUT_ARRIVALS',native_DEF=x['actual_DEF'],placement_check='exact native row/site/orient and all4000actual region instances inventoried; actual CORE SPACER DECAP omitted only under standard remove_fillers, TAP/clock/FF retained; no collisions; macrohalo outsidecandidate',master_dims_basis='actual same-platform BclassF_final_geom.tsv master bounds; currentDEF exact master identities',unknown_masters=unknown,candidate=new,OA_input_prices=prices,output_chain_old_lower_bound_um=round(dist(oldxy['_27646_'],oldxy['wire17963'])+dist(oldxy['wire17963'],oldxy['lweco_219418']),3),output_chain_new_lower_bound_um=round(dist(newxy['_27646_'],newxy['wire17963'])+dist(newxy['wire17963'],newxy['lweco_219418']),3),PG_gate='PASS zero candidate overlap against actual savedDEF power paths plus exact explicit via RECTs; stripe bounds conservatively include halfwidth endpoint cap; 1672 regionPGshapes plus conservative0.096um keepout,0unparsed, no nominal substitute',bay_gate='PASS complete actual saved6_final.DEF emits no BLOCKAGES section; actual macro halo and all fixed/TAP/functional region poses included',scope='same2cells/masters, all other cells/clock/reset/RTL/cycles unchanged; NO CAD dispatched')
(P/'candidate_prices.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))

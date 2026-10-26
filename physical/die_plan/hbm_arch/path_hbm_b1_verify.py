"""D-HBM-B1 item verification + die-wide per-bit FT census (geometry only; no route/timing claim).
Usage: b1_verify.py <tools/die_plan dir> <plan_dir> <out.json>"""
import sys,json,hashlib,collections,numpy as np
from pathlib import Path
sys.path[:0]=[sys.argv[1]];import schema as S,check as C
from gen_phys import type_pins
pd=Path(sys.argv[2]);pp=pd/'die_plan.json';raw=json.load(open(pp));P=S.Plan(json.loads(json.dumps(raw)),str(pp))
rep=dict(plan=str(pp),sha256=hashlib.sha256(pp.read_bytes()).hexdigest())
# 1 M5 ceiling
bad=[];pinbad=collections.Counter();ncore=0
for tn,t in raw['partition_types'].items():
 for c in t.get('hard_cores',[]):
  ncore+=1
  if c.get('obs_max')!='M5':bad.append((tn,c['inst'],c.get('obs_max')))
  pf=c.get('pins_file')
  if pf and (pd/pf).exists():
   js=json.load(open(pd/pf));pins=js.get('pins',js) if isinstance(js,dict) else js
   it=pins.values() if isinstance(pins,dict) else pins
   for q in it:
    L=(q.get('layer') if isinstance(q,dict) else None)
    if L and L not in ('M4','M5'):pinbad[(tn,c['inst'],L)]+=1
  elif pf:pinbad[(tn,c['inst'],'MISSING_PINS_FILE')]+=1
rep['m5_ceiling']=dict(cores=ncore,obs_not_m5=bad[:20],n_obs_not_m5=len(bad),pins_not_m4m5=len(pinbad),pins_examples=[list(k)+[v] for k,v in list(pinbad.items())[:10]])
# 4 clock taps inside outline
off=[]
for tn,t in raw['partition_types'].items():
 w,h=t['outline_um'];ck=t.get('clock') or {}
 pts=[('tap_um',ck['tap_um'])] if ck.get('tap_um') else []
 pts+=[(x.get('name'),x['xy']) for x in ck.get('taps',[]) if 'xy' in x]
 for n,(x,y) in pts:
  if not(-1e-6<=x<=w+1e-6 and -1e-6<=y<=h+1e-6):off.append((tn,n,[x,y],[w,h]))
rep['clock_taps_off_outline']=off;rep['q_su11_clock']=dict(tap_um=raw['partition_types']['q_su11']['clock'].get('tap_um'),outline=raw['partition_types']['q_su11']['outline_um'],off=[o for o in off if o[0]=='q_su11'])
# 2 spu1 bands
rep['q_spu1_bands']=raw['partition_types']['q_spu1'].get('die_ft_bands')
# 3 per-part max cut ratio
geo={lid:C.lane_geometry(P,lid) for lid in P.lanes}
src=__import__('inspect').getsource(C.check_cuts).replace("            if loc:\n","            ALL.extend(loc)\n            if loc:\n",1)
ns=C.__dict__;ns['ALL']=[];exec(src,ns);R=C.Report();out=ns['check_cuts'](P,R,geo)
mx=collections.defaultdict(float)
for r,pn,b,cap in ns["ALL"]:
 tk=P.parts[pn]["type"] if pn in P.parts else pn;mx[tk]=max(mx[tk],r)
rep['cut_max_by_type']={k:round(v,4) for k,v in sorted(mx.items(),key=lambda kv:-kv[1])}
rep['cut_errors']=[i['msg'] for i in R.items if i['level']=='ERROR']
# per-bit census
cen={};tot_ff=0;fails=[]
for tn,t in P.types.items():
 slots=[s for s in t.get('ft_slots',[]) if s.get('bit_sites_um')]
 nos=[s['name'] for s in t.get('ft_slots',[]) if not s.get('bit_sites_um') and s.get('stations',0)>1]
 if not slots:
  if t.get('ft_slots'):cen[tn]=dict(slots=len(t['ft_slots']),per_bit_slots=0,no_sites=nos)
  continue
 w,h=t['outline_um'];pins={(b,i):np.array([x,y]) for b,i,_,x,y,_ in type_pins(P,tn)}
 boxes=list(S.placed_macro_boxes(t,halo=8.64).values());seen=set();worst=(0,None);ff=0;f=[]
 for s in slots:
  n=s['width']+1;nm=s['name'];pts=np.array(s['bit_sites_um']);cell=np.array(s.get('bit_site_cell_um',[1.404,.27]))
  if len(pts)!=s['stations']-1:f.append((nm,'stations/site mismatch',len(pts),s['stations']));continue
  try:chain=[np.array([pins[nm+'_i',i] for i in range(n)]),*[a+cell/2 for a in pts],np.array([pins[nm+'_o',i] for i in range(n)])]
  except KeyError as e:f.append((nm,'pin missing',str(e)));continue
  for a,b in zip(chain,chain[1:]):
   hm=float(np.abs(a-b).sum(axis=1).max())
   if hm>worst[0]:worst=(hm,nm)
  for st in pts:
   if not((st>=-1e-6)&(st+cell<=np.array([w,h])+1e-6)).all():f.append((nm,'site off outline'))
   for x0,y0,x1,y1 in boxes:
    k=int(((st[:,0]<x1-1e-6)&(st[:,0]+cell[0]>x0+1e-6)&(st[:,1]<y1-1e-6)&(st[:,1]+cell[1]>y0+1e-6)).sum())
    if k:f.append((nm,'halo collision',k))
   for x,y in st:
    key=(round(x,3),round(y,3))
    if key in seen:f.append((nm,'FF collision',key))
    seen.add(key)
   ff+=len(st)
 if worst[0]>403+1e-6:f.append(('worst hop',round(worst[0],2),worst[1]))
 tot_ff+=ff;cen[tn]=dict(slots=len(t['ft_slots']),per_bit_slots=len(slots),no_sites=nos,ff_sites=ff,max_bit_hop_um=round(worst[0],3),worst_slot=worst[1],failures=f[:10],n_fail=len(f))
 if f:fails.append(tn)
rep['perbit_census']=dict(types=cen,total_ff_sites=tot_ff,fail_types=fails,verdict='PASS' if not fails else 'FAIL')
json.dump(rep,open(sys.argv[3],'w'),indent=1,default=str)
print(json.dumps({k:v for k,v in rep.items() if k not in('perbit_census','q_spu1_bands')},default=str)[:3000])
print('census',rep['perbit_census']['verdict'],tot_ff,fails,{k:(v.get('per_bit_slots'),v.get('max_bit_hop_um'),v.get('n_fail'),len(v.get('no_sites',[]))) for k,v in cen.items()})

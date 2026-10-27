#!/usr/bin/env python3
"""Prepare the last S81 G2 storage-band fix; geometry only, never qualifies a route."""
import argparse,copy,hashlib,json,math,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--tools',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--sidecar',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();sys.path.insert(0,a.tools)
import schema as S,gen_phys as G,clock_landing_plan as C,ft_bit_sites as F
raw=Path(a.plan).read_bytes();assert hashlib.sha256(raw).hexdigest()=='9fdf967b6db88c90f1cb0ea0b8ad43c35bf6644f0fad03a33eff12d83953b936','wrong adopted fallback input'
p=json.loads(raw);side=json.load(open(a.sidecar));pn=next(x for x in p['partitions'] if x['name']=='svc_13');tn=pn['type'];t=p['partition_types'][tn];old=copy.deepcopy(t);assert len(t['hard_cores'])==72
for c in t['hard_cores']:c['origin_um'][0]=round(c['origin_um'][0]-25.92,6)
for fs in t['ft_slots']:
 if fs['name']!='ft_dl0':fs['bit_sites_um']=[[[round(x-25.92,6),y] for x,y in bs] for bs in fs['bit_sites_um']]
 else:
  banks=[]
  for bs in fs['bit_sites_um']:
   nr=math.ceil(len(bs)/8);yc=(min(y for x,y in bs)+max(y for x,y in bs))/2;yb=round((yc-(nr-1)*.54/2)/.27)*.27
   banks.append([[round(1386.342+(i%8)*1.62,6),round(yb+(i//8)*.54,6)] for i in range(len(bs))])
  fs['bit_sites_um']=banks
 fs['regs_um']=[fs['regs_um'][0]]+[[round(sum(x for x,y in b)/len(b),6),round(sum(y for x,y in b)/len(b),6)] for b in fs['bit_sites_um']];F.validate_slot(fs)
used=[v['rect_um'] for k,v in t['clock']['landing_contract']['bands'].items() if k!='attn_i0' and v.get('rect_um')];band=C._storage_band(t,'attn_i0',4017,used);band['instance']='u_cland_attn_i0';t['clock']['landing_contract']['bands']['attn_i0']=band
side['collector']['types'][tn]['bands']['attn_i0']=copy.deepcopy(band);fail=side['collector']['placement_failures'];assert len(fail)==1 and fail[0]['type']==tn and fail[0]['bus']=='attn_i0';side['collector']['placement_failures']=[];side['collector']['physical_qualified']=False
P=S.Plan(p);pins={}
for bus,bit,layer,x,y,face in G.type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y)
def census(q):
 boxes=S.placed_macro_boxes(q);hits=[];hops={}
 for f in q['ft_slots']:
  w,h=f['bit_site_cell_um'];bs=f['bit_sites_um'];mx=0
  for bit in range(f['width']+1):
   chain=[pins[f['name']+'_i'][bit]]+[(b[bit][0]+w/2,b[bit][1]+h/2) for b in bs]+[pins[f['name']+'_o'][bit]]
   mx=max(mx,max(abs(x-u)+abs(y-v) for (x,y),(u,v) in zip(chain,chain[1:])))
  hops[f['name']]=round(mx,6)
  for j,b in enumerate(bs):
   for bit,(x,y) in enumerate(b):
    if any(min(x+w,r[2])>max(x,r[0])+1e-6 and min(y+h,r[3])>max(y,r[1])+1e-6 for r in boxes.values()):hits.append([f['name'],j,bit])
 return dict(maxhop_um=hops,ft_macro_body_hits=len(hits),examples=hits[:3])
r=dict(status='GEOMETRY_CANDIDATE_NOT_PHYSICALLY_QUALIFIED',type=tn,source_plan_sha256=hashlib.sha256(raw).hexdigest(),added_cycles=0,outline_unchanged=t['outline_um']==old['outline_um'],before=census(old),after=census(t),landing_band=band,storage_failures_remaining=0)
for f in t['ft_slots']:
 w,h=f['bit_site_cell_um'];W,H=t['outline_um']
 assert all(4.32<=x and 4.32<=y and x+w<=W-4.32 and y+h<=H-4.32 for b in f['bit_sites_um'] for x,y in b),f['name']
assert r['after']['ft_macro_body_hits']==0,r
assert max(r['after']['maxhop_um'].values())<=405,r
assert min(x['origin_um'][0] for x in t['hard_cores'])>=4.32
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
for name,v in [('die_plan.json',p),('landed_sidecar.json',side),('REPORT.json',r)]: (out/name).write_text(json.dumps(v,indent=1)+'\n')
print(json.dumps(r,indent=1))

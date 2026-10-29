#!/usr/bin/env python3
"""Find same-outline source relayouts for blocked S81 landing bands. No adoption."""
import copy,json,sys,concurrent.futures,math
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import clock_landing_plan as CL, schema as S, gen_phys as G
raw=json.load(open(sys.argv[1]));sc=json.load(open(sys.argv[2]));dest=Path(sys.argv[3]);dest.mkdir(parents=True,exist_ok=True)
failed={r['type'] for r in sc['collector']['placement_failures']}
for a in sys.argv[4:]:
 if a.startswith('--only='):failed &= {a.split('=',1)[1]}
if '--complete-aspect' in sys.argv[4:]:CL.BAND_ASPECT_GRID=True
def work(tn):
 base=raw['partition_types'][tn];info=sc['collector']['types'][tn]; w,h=base['outline_um'];rows=[]
 translations=[(0,0),(0,25.92),(0,34.56),(25.92,0),(-25.92,0),(0,-25.92),(25.92,25.92),(-25.92,25.92),(25.92,-25.92),(-25.92,-25.92),(25.92,34.56),(34.56,34.56),(0,51.84)]
 if '--bank-relief' in sys.argv[4:]:translations=[(34.56,0),(25.92,0),(34.56,8.64)]
 for dx,dy in translations:
  t=copy.deepcopy(base)
  t['_cland_geom']=copy.deepcopy(info.get('bus_geometry',{}))
  for child in info.get('children',[]):
   if child.get('seam'):t.setdefault('buses',[]).append(CL._scalar(t,'cland_dn_ready_'+str(child['index']),'in',child['xy_um'],'ctl',shift=4.32))
  for c in t.get('hard_cores',[]):c['origin_um']=[round(c['origin_um'][0]+dx,6),round(c['origin_um'][1]+dy,6)]
  if any(c['origin_um'][0]<4.32-1e-5 or c['origin_um'][1]<4.32-1e-5 or c['origin_um'][0]+c['outline_um'][0]>w-4.32+1e-5 or c['origin_um'][1]+c['outline_um'][1]>h-4.32+1e-5 for c in t.get('hard_cores',[])):continue
  for f in t.get('ft_slots',[]):
   if f.get('regs_um'):f['regs_um']=[f['regs_um'][0]]+[[round(x+dx,6),round(y+dy,6)]for x,y in f['regs_um'][1:]]
   if f.get('bit_sites_um'):f['bit_sites_um']=[[[round(x+dx,6),round(y+dy,6)]for x,y in st]for st in f['bit_sites_um']]
  bank_relief=[]
  if '--bank-relief' in sys.argv[4:]:
   for f in t.get('ft_slots',[]):
    if f['name']!='ft1':continue
    for j,st in enumerate(f.get('bit_sites_um',[])):
     ox=min(q[0] for q in st)-dx;oy=min(q[1]for q in st)-dy
     if ox<60 and 900<oy<1600:
      f['bit_sites_um'][j]=[[round(x-dx,6),y]for x,y in st]
      f['regs_um'][j+1][0]=round(f['regs_um'][j+1][0]-dx,6)
      bank_relief.append(dict(slot=f['name'],internal_stage=j+1,delta_um=[-dx,0]))
  used=[];bands={};errs=[]
  band_items=list(info['bands'].items())
  if '--largest-first' in sys.argv[4:]:
   band_items.sort(key=lambda item:(item[0].startswith('monitor_'),-(item[1].get('width') or (2 if item[0].startswith('monitor_') else CL._bus_geom(t,item[0])['width'])),item[0]))
  for bus,b in band_items:
   try:
    # Match data-band allocation first; collector bands follow in the original compose.
    geom_bus='cland_dn_ready_'+bus[len('monitor_'):] if bus.startswith('monitor_') else bus
    width=b.get('width',CL._bus_geom(t,geom_bus)['width'])
    q=CL._storage_band(t,geom_bus,width,used,has_epoch=not bus.startswith('monitor_'))
    used.append(q['rect_um']);bands[bus]=q
   except Exception as e:errs.append(dict(bus=bus,error=str(e)))
  result=dict(type=tn,translation_um=[dx,dy],bank_relief=bank_relief,bands_failed=len(errs),failures=errs,bands=bands)
  if not errs:
   # FT stations retain stage count, exact per-bit pin endpoints and cell footprint.
   P=S.Plan(raw);P.types[tn]=t; pins={}
   for bus,bit,L,x,y,face in G.type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y)
   worst=0;over=0
   for f in t.get('ft_slots',[]):
    if not f.get('bit_sites_um'):continue
    cw,ch=f['bit_site_cell_um'];a=pins[f['name']+'_i'];b=pins[f['name']+'_o']
    for bit in set(a)&set(b):
     q=[a[bit]]+[(stage[bit][0]+cw/2,stage[bit][1]+ch/2)for stage in f['bit_sites_um']]+[b[bit]]
     v=max(abs(x[0]-y[0])+abs(x[1]-y[1])for x,y in zip(q,q[1:]));worst=max(worst,v);over+=v>405+1e-5
   result.update(ft_all_bit_max_hop_um=worst,ft_bits_over405=over)
  rows.append(result)
  print('SHIFT',tn,dx,dy,'bandfails',len(errs),'ft',result.get('ft_all_bit_max_hop_um'),flush=True)
  if not errs and result['ft_bits_over405']==0:
   json.dump(dict(type=tn,translation_um=[dx,dy],bands=bands,bank_relief=bank_relief,band_order='largest_first' if '--largest-first' in sys.argv[4:] else 'name',band_aspect_grid=getattr(CL,'BAND_ASPECT_GRID',False)),open(dest/(tn+'.candidate.json'),'w'),indent=1)
   break
 json.dump(dict(type=tn,candidates=rows),open(dest/(tn+'.json'),'w'),indent=1)
 return dict(type=tn,tries=len(rows),landing_and_ft_feasible=bool(rows and not rows[-1]['bands_failed'] and rows[-1].get('ft_bits_over405')==0))
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=8) as ex:r=list(ex.map(work,sorted(failed)))
 json.dump(r,open(dest/'summary.json','w'),indent=2);print(json.dumps(r),flush=True)

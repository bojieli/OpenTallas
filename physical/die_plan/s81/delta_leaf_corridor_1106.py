#!/usr/bin/env python3
"""Private S81 t13 corridor form. Preserve RTL/pins/stage counts/cycles.

Re-site existing physical groups only. Actual routed timing remains owed.
"""
import argparse
import json
import copy
from pathlib import Path


def apply(plan):
 old=plan['partition_types']['ot_s81sl_leaf__t13'];t=copy.deepcopy(old)
 origins={'u_lf.u_ve.u_m':[155.52,812.16],'u_lf.u_ve.u_s':[336.96,812.16],'u_lf.u_vq':[518.4,1062.72],'u_lf.u_vp.u_b1':[699.84,1088.64]}
 expected={'u_lf.u_ve.u_m':[43.2,838.08],'u_lf.u_ve.u_s':[224.64,838.08],'u_lf.u_vq':[414.72,950.4],'u_lf.u_vp.u_b1':[682.56,1088.64]}
 for h in t['hard_cores']:
  if h['inst'] in expected:assert h['origin_um']==expected[h['inst']],h['inst']
 deltas={h['inst']:[origins[h['inst']][i]-h['origin_um'][i] for i in range(2)] for h in t['hard_cores'] if h['inst'] in origins}
 def delta_name(name):
  for n,d in deltas.items():
   if name.removeprefix('core:')==n or name.removeprefix('core:').startswith(n+'.'):return d
  return [0,0]
 def add(a,d):return [round(a[i]+d[i],6) for i in range(2)]
 pointmap={}
 def move(a,d):pointmap[tuple(round(x,6) for x in a)]=add(a,d)
 for h in t['hard_cores']:
  if h['inst'] in origins:h['origin_um']=origins[h['inst']]
 for row in old['clock']['taps']:
  d=delta_name(row['name'])
  if d!=[0,0]:move(row['xy'],d)
 for row in old['clock']['landing_contract']['collector_tree']['core_resets']:
  d=delta_name(row['inst'])
  if d!=[0,0]:
   move(row['xy'],d);move(row['pin_um'],d)
 # Ring read-side taps and a dedicated VE_s-side tap track their physical groups.
 for src,d in [([410.4,941.76],[112.32,-25.92]),([493.614,1173.96],[-148.014,-3.24]),([468.706,1197.72],[-235.426,0]),([298.08,805.64],[0,-2.108])]:move(src,d)
 # Fixed RTL FT stage counts, exact existing per-bit footprint translated.
 changes={('ft1',0):[360.72,1200.96],('ft1',1):[140.4,1123.2],('ft2',3):[95.04,993.6],('ft3',4):[129.6,976.32]}
 for slot in t['ft_slots']:
  for i,sites in enumerate(slot['bit_sites_um']):
   target=changes.get((slot['name'],i))
   if target:
    center=slot['regs_um'][i+1];d=[target[k]-center[k] for k in range(2)];move(center,d);slot['bit_sites_um'][i]=[add(x,d) for x in sites]
 # Native macro-aware grid keeps its sixteen tap names but three sites move.
 for a,b in [([180.36,814.32],[145.8,814.32]),([180.36,1194.48],[145.8,1073.52]),([541.08,1090.8],[541.08,1054.08])]:move(a,[b[k]-a[k] for k in range(2)])
 rectmap={(403.92,1185.84,533.492,1209.6):[155.52,1185.84,285.092,1209.6],(429.888,1162.08,557.34,1185.84):[285.12,1162.08,412.572,1185.84]}
 def remap(x,key=''):
  if key in ('bit_sites_um','origin_um'):return x
  if isinstance(x,dict):return {k:remap(v,k) for k,v in x.items()}
  if isinstance(x,list):
   if len(x) in (2,4) and all(isinstance(v,(int,float)) for v in x):
    v=tuple(round(z,6) for z in x)
    if len(x)==2 and v in pointmap:return pointmap[v]
    if len(x)==4 and v in rectmap:return rectmap[v]
   return [remap(v,key) for v in x]
  return x
 t=remap(t)
 # Re-site existing reset flops only; names, drivers, Q, depths and taps stay fixed.
 reset_sites={70:[514.08,1084.32],110:[850.68,1135.68],114:[1306.8,1144.32],125:[912.6,1144.32],126:[514.08,1144.32],130:[330.48,946.08],131:[145.8,833.76],167:[550.8,1216.08],170:[505.44,1216.08],234:[330.48,833.76],243:[330.48,928.76]}
 for row in t['clock']['landing_contract']['collector_tree']['relays']:
  idx=int(row['name'][6:])
  if idx in reset_sites:row['xy']=reset_sites[idx]
 # Internal core-to-core endpoint coordinates follow the actual moved macro pins.
 for row in t['internal_stations']:
  row['from_um']=add(row['from_um'],delta_name(row['launch']));row['to_um']=add(row['to_um'],delta_name(row['capture']))
 # Check real FT bit identities, not just center/rectangle reach.
 def inside(pt,h):
  x,y=pt;X,Y=h['origin_um'];w,hh=h['outline_um'];return X<x+1.404 and x<X+w and Y<y+.27 and y<Y+hh
 bad=[];reach=[]
 for slot in t['ft_slots']:
  for i,sites in enumerate(slot['bit_sites_um']):
   for bit,pt in enumerate(sites):
    hits=[h['inst'] for h in t['hard_cores'] if inside(pt,h)]
    if hits:bad.append([slot['name'],i,bit,pt,hits])
  for i in range(len(slot['bit_sites_um'])-1):
   aa,bb=slot['bit_sites_um'][i:i+2];reach.append([slot['name'],i,i+1,max(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(aa,bb))])
 ibad=[]
 for i,row in enumerate(t['internal_stations']):
  pts=[row['from_um']]+row['regs_um']+[row['to_um']];hops=[sum(abs(a[k]-b[k]) for k in (0,1)) for a,b in zip(pts,pts[1:])]
  for j,pt in enumerate(row['regs_um']):
   hits=[h['inst'] for h in t['hard_cores'] if inside(pt,h)]
   if hits:ibad.append([i,j,row['conn'],pt,hits])
  if max(hops,default=0)>402.84:ibad.append([i,'reach',row['conn'],max(hops)])
 report={'macro_origins':origins,'ft_macro_overlaps':bad,'ft_pairwise_hops_um':reach,'internal_conflicts_or_reach':ibad,'point_alias_moves':[[list(k),v] for k,v in pointmap.items()]}

 assert len(t['hard_cores'])==len(old['hard_cores'])==27
 assert t['outline_um']==old['outline_um'] and t['buses']==old['buses']
 assert not bad and not ibad
 assert max(x[-1] for x in reach)<=402.84
 for a,z in zip(old['ft_slots'],t['ft_slots']):
  assert a['stations']==z['stations'] and len(a['bit_sites_um'])==len(z['bit_sites_um'])
  for k in ['in_face','out_face','width','in_window_um','out_window_um','layers','order']:assert a[k]==z[k]
  assert [len(x) for x in a['bit_sites_um']]==[len(x) for x in z['bit_sites_um']]
 r=t['clock']['landing_contract']['collector_tree'];previous=old['clock']['landing_contract']['collector_tree']
 assert len(r['relays'])==len(previous['relays'])
 for a,z in zip(previous['relays'],r['relays']):assert {k:v for k,v in a.items() if k!='xy'}=={k:v for k,v in z.items() if k!='xy'}
 xy={'rst_root_n':r['root']}|{x['q']:x['xy'] for x in r['relays']}
 reset_hops=[sum(abs(a['xy'][i]-xy[a['d']][i]) for i in (0,1)) for a in r['relays'] if a['d'] in xy]
 assert max(reset_hops)<=402.84
 assert not [(a['name'],h['inst']) for a in r['relays'] for h in t['hard_cores'] if inside(a['xy'],h)]
 r['max_hop_um']=round(max(reset_hops),6)
 # Entire input pin windows/capture bands and output windows are conservative
 # bounds in addition to matching the actual FT bit identity between stages.
 def dist(a,b):return sum(abs(a[i]-b[i]) for i in (0,1))
 W,H=t['outline_um'];boundary=[];bands=t['clock']['landing_contract']['bands']
 for slot in t['ft_slots']:
  def pins(k):
   f=slot[k+'_face'];return [[v,H if f=='N' else 0] for v in slot[k+'_window_um']] if f in ['N','S'] else [[W if f=='E' else 0,v] for v in slot[k+'_window_um']]
  first,last=slot['bit_sites_um'][0],slot['bit_sites_um'][-1];band=bands.get(slot['name']+'_i')
  if band:
   x,y,X,Y=band['rect_um'];corners=[[a,z] for a in (x,X) for z in (y,Y)]
   entry=max(dist(a,z) for a in pins('in') for z in corners);post=max(dist(a,z) for a in corners for z in first)
   band['max_pin_to_band_hop_um']=round(entry,6)
  else:entry=max(dist(a,z) for a in pins('in') for z in first);post=0
  output=max(dist(a,z) for a in last for z in pins('out'));assert max(entry,post,output)<=402.84
  boundary.append({'slot':slot['name'],'pin_entry_um':entry,'ring_to_first_stage_um':post,'last_stage_to_pin_um':output})
 for row in t['clock']['landing_contract']['collector_local_sources']:
  if row['name'] in ('ft0_i','ft1_i'):row['band']=copy.deepcopy(bands[row['name']])
 report.update({'ft_max_paired_bit_hop_um':max(x[-1] for x in reach),'boundary_corner_hops':boundary,'reset_max_hop_um':max(reset_hops),'reset_flops':len(r['relays']),'macro_count':27,'data_added_cycles':0,'control_added_cycles':0,'rtl_changed':False,'pins_changed':False,'physical_status':'NOT RUN'})
 return t,report

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('plan',type=Path);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 p=json.loads(args.plan.read_text());t,r=apply(p);p['partition_types']['ot_s81sl_leaf__t13']=t
 args.out.mkdir(parents=True,exist_ok=True)
 for name,value in [('type.json',t),('plan.json',p),('event.json',r)]:
  (args.out/name).write_text(json.dumps(value,indent=1)+'\n')
 print('t13 form: 27 macros, paired FT hop',r['ft_max_paired_bit_hop_um'],'reset hop',r['reset_max_hop_um'])

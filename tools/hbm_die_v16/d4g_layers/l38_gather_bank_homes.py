#!/usr/bin/env python3
"""Place source-bound gather cells beside actual VM faces, preserving all bodies.

This constructs requested soft grants, not hardened views or qualified timing.
A bounded local search may report no fit. It never moves an existing body or
uses retained relay corridors, root keepouts or old column-envelope aliases.
"""
import argparse, gzip, hashlib, json, math
from pathlib import Path

def load(p):
 p=Path(p); b=p.read_bytes(); return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def overlap(a,b): return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6
class Occupancy:
 def __init__(self,W,H,rects):
  self.W=W;self.H=H;self.buckets={};self.rects=[]
  for name,r in rects:self.add(name,r)
 def keys(self,r):
  for x in range(math.floor(r[0]/256),math.floor(r[2]/256)+1):
   for y in range(math.floor(r[1]/256),math.floor(r[3]/256)+1):yield x,y
 def add(self,name,r):
  idx=len(self.rects);self.rects.append((name,r))
  for k in self.keys(r):self.buckets.setdefault(k,[]).append(idx)
 def hits(self,r):
  if r[0]<0 or r[1]<0 or r[2]>self.W or r[3]>self.H:return ['DIE_BOUNDARY']
  ids=set(i for k in self.keys(r) for i in self.buckets.get(k,[]))
  return [self.rects[i][0] for i in ids if overlap(r,self.rects[i][1])]

def snap(x):return round(x/8.64)*8.64

def place(g,base,roots,source,cut,pins,clocks,variant):
 W,H=g['die_um']; retained={n:dict(v) for n,v in base['placement'].items() if n not in g['automatic_relays_requiring_regeneration'] and n!='hc_eng'}
 retained.update(g['existing_bodies_moved']);retained['hc_eng']=g['placed_service_envelopes']['hc_eng']
 rects=[(n,(v['x'],v['y'],v['x']+v['w'],v['y']+v['h'])) for n,v in retained.items()]
 rects += [(n,(v['x_um'],v['y_um'],v['x_um']+v['width_um'],v['y_um']+v['height_um'])) for n,v in g['individual_source_rectangles'].items()]
 rects += [('ROOT:'+s['region'],s['keepout']) for s in roots['sites']]
 for i,b in enumerate(source['last_step_postcut_bands']):
  rects.append(('INSERTION_CORRIDOR:'+str(i),(b['start_um'],0,b['end_um'],H) if b['axis']=='x' else (0,b['start_um'],W,b['end_um'])))
 occ=Occupancy(W,H,rects);banks=[];failed=[]
 bw,bh=cut['grant_requests']['bank_local']['outline_'+variant+'_um']
 for b in cut['banks']:
  name=b['VM_bank'];v=retained[name];target=pins['instances'][name]
  # Exact existing native bank W client pin centroids remain the destination.
  native={p:target[p] for p in ('rq0','rr0','wq0','wq_done0')};tx=sum(p[0] for p in native.values())/4;ty=sum(p[1] for p in native.values())/4
  choices=[]
  for dx in range(0,35):
   x=snap(v['x']-21.6-bw-dx*8.64)
   for dy in range(-36,37):
    y=snap(ty-bh/2+dy*8.64);r=(x,y,x+bw,y+bh)
    reach=max(abs(x+bw-p[0])+abs(y+bh/2-p[1]) for p in native.values())
    if reach>405:continue
    score=abs(x+bw-tx)+abs(y+bh/2-ty)
    choices.append((score,x,y,reach,r))
  picked=None
  for _,x,y,reach,r in sorted(choices):
   if not occ.hits(r):picked=(x,y,reach,r);break
  if picked is None:
   failed.append(dict(bank=name,cause='NO_LEGAL_NEAR_W_FACE_GRANT_WITHIN_405_UM',next_action='Use explicit longer source-bound delivery and equal-age return route; no body move or corridor consumption'))
   continue
  x,y,reach,r=picked;occ.add('GATHER_BANK:'+name,r)
  faces=cut['grant_requests']['bank_local']['face_data_bits'];assert faces['W']<=bh*3.6 and faces['E']<=bh*3.6 and faces['N']<=bw*3.6
  banks.append(dict(bank=name,bank_index=b['bank'],x=x,y=y,w=bw,h=bh,header=b['cell'],selector='gather_sel_'+name[4:],clock_terminals=['header.clk','selector.clk'],core_links=b['core_links'],native_pin_centroids=native,bank_centroid_bound_um=reach,face_bits=faces,access_policy='6 pins/um; 60 percent face cap; E/W M4, N/S M5',status='PLACED_SOFT_SOURCE_GRANT_NOT_QUALIFIED_VIEW'))
 cw,ch=cut['grant_requests']['core']['outline_'+variant+'_um'];cx=sum(b['x'] for b in banks)/max(1,len(banks));cy=sum(b['y'] for b in banks)/max(1,len(banks));core=None
 # One actual central grant, bounded search only; existing geometry is fixed.
 candidates=[]
 for dx in range(-48,49):
  for dy in range(-48,49):
   x=snap(cx-cw/2+dx*43.2);y=snap(cy-ch/2+dy*43.2)
   candidates.append((abs(dx)+abs(dy),x,y))
 for _,x,y in sorted(candidates):
  r=(x,y,x+cw,y+ch)
  if not occ.hits(r):
   core=dict(x=x,y=y,w=cw,h=ch,master=cut['grant_requests']['core']['master'],face_bits=cut['grant_requests']['core']['face_data_bits'],clock_terminals=['clk'],status='PLACED_SOFT_SOURCE_GRANT_NOT_QUALIFIED_VIEW');occ.add('GATHER_CORE',r);break
 if core is None:failed.append(dict(cause='NO_LEGAL_CENTRAL_PIN_BOUNDED_GRANT',next_action='Source-bound distributed control projection using only enumerated actual cells'))
 clock_conflicts=[]
 newrects=[('bank:'+b['bank'],(b['x'],b['y'],b['x']+b['w'],b['y']+b['h'])) for b in banks]
 if core:newrects.append(('core',(core['x'],core['y'],core['x']+cw,core['y']+ch)))
 for tree in clocks['clock_trees'].values():
  for n,m,x,y in tree['buffers']:
   # Both actual canonical buffer masters have the reserved full cell box.
   hit=[k for k,r in newrects if overlap((x,y,x+1.62,y+.27),r)]
   if hit:clock_conflicts.append(dict(cell=n,master=m,source_xy=[x,y],intersecting_grants=hit))
 routes=[]
 if core:
  for b in banks:
   distance=abs(core['x']+cw/2-b['x']-bw/2)+abs(core['y']+ch/2-b['y']-bh/2)
   routes.append(dict(bank=b['bank'],manhattan_centroid_um=distance,outbound_header_data_bits=82,selector_reserve_bits=1,return_data_valid_bits=33,reset_bits=1,source_bit_order='See literal core_links; no masks/status/reset removed',payload_edges=None,return_edges=None,boot_edges=None,clock_compensation=None))
 return dict(variant=variant,status='PLACED_SOURCE_GRANTS_ROUTES_OPEN' if not failed else 'PARTIAL_NAMED_HOME_FAILURE',source='0c55c33fc',bank_grants=banks,core_grant=core,failures=failed,bank_grant_count=len(banks),retained_existing_bodies=len(retained),retained_column_rectangles=len(g['individual_source_rectangles']),root_keepouts=len(roots['sites']),insertion_corridors=len(source['last_step_postcut_bands']),existing_bodies_moved_by_this_step=0,clock_cells_requiring_new_revision_rehome=clock_conflicts,route_requests=routes,pin_registration='NOT_EVALUATED',fixed_calendar='OPEN until real routed delivery/return and propagated clock ages',native_component_profile='R10/W5, launch +4; not inherited for die travel')

if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__)
 for n in ('geometry','baseline','roots','source','cut','pins','clocks','out'):a.add_argument('--'+n,required=True,type=Path)
 p=a.parse_args();args={k:load(getattr(p,k)) for k in ('geometry','baseline','roots','source','cut','pins','clocks')}
 result=dict(source_readset_sha256={k:hashlib.sha256(getattr(p,k).read_bytes()).hexdigest() for k in args},variants=[place(args['geometry'],args['baseline'],args['roots'],args['source'],args['cut'],args['pins'],args['clocks'],v) for v in ('MAIN','FB')])
 p.out.write_text(json.dumps(result,indent=1)+'\n')
 for r in result['variants']:print(r['variant'],r['status'],'banks',r['bank_grant_count'],'core',bool(r['core_grant']),'clock rehomes',len(r['clock_cells_requiring_new_revision_rehome']))

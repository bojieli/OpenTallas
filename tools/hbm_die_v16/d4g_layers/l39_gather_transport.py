#!/usr/bin/env python3
"""Construct existing relay-family capacity plans for literal gather grants.

The output is a station/edge construction request, never physical signoff.
Equal-age padding is booked against the same capacity map as every route.
Reset and clock delivery retain their own downstream construction obligations.
"""
import argparse, gzip, hashlib, json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from l38_gather_bank_homes import load
import relay_router as RR
import relay_lanes_d4f as RL

def run(g,base,roots,clocks,grants,variant):
 placement={n:dict(v) for n,v in base['placement'].items() if n not in g['automatic_relays_requiring_regeneration'] and n!='hc_eng'}
 placement.update(g['existing_bodies_moved']);placement['hc_eng']=g['placed_service_envelopes']['hc_eng']
 for n,v in g['individual_source_rectangles'].items():placement[n]=dict(m='literal_Col8',x=v['x_um'],y=v['y_um'],w=v['width_um'],h=v['height_um'])
 v=next(v for v in grants['variants'] if v['variant']==variant);assert not v['failures'] and not v['clock_cells_requiring_new_revision_rehome']
 for b in v['bank_grants']:placement['gather_bank_'+b['bank']]=dict(m='soft_gather_header_selector',**{k:b[k] for k in ('x','y','w','h')})
 core=v['core_grant'];placement['gather_core']=dict(m=core['master'],**{k:core[k] for k in ('x','y','w','h')})
 keep=[s['keepout'] for s in roots['sites']]
 for t in clocks['clock_trees'].values():keep.extend((x,y,x+1.62,y+.27) for n,m,x,y in t['buffers'])
 router=RR.Router(placement,g['die_um'],405,G=10,macro_cost=4,carved=base.get('carved_feedthrough'),keepouts=keep)
 cap=RL.Capacity(router,.5,50,2);requests=[]
 for b in v['bank_grants']:
  q=b['bank_index']//8;k=b['bank_index']%8;face=('W','S','N','E')[q]
  # Literal core bank links occupy contiguous, ordered 116-bit intervals.
  # The full 6-pin/um span is retained rather than treating pins as one point.
  vertical=face in ('W','E');face_length=core['h'] if vertical else core['w'];nface=core['face_bits'][face]
  along=(face_length-nface/6)/2+(k*116+58)/6
  cp=(core['x']+(0 if face=='W' else core['w']) if vertical else core['x']+along,
      core['y']+along if vertical else core['y']+(core['h'] if face=='N' else 0))
  bp=(b['x']+b['w']/2,b['y']+b['h'])
  for direction,P,bits in [('outbound',[cp,bp],83),('return',[bp,cp],33)]:
   path=router.route(P[0],P[1]);_,sa=router.node(P[0]);_,sb=router.node(P[1]);paths={1:(np.asarray(path,dtype=np.int64),sa,sb)}
   width=48 if bits<=48 else 624;tiles=math.ceil(bits/width);fp=tiles*RL.tile_um(width)**2*1.2
   sl,tail,dep,bad=RL.plan_bus_cap(router,cap,P,{1:0},300,width,[b['bank']],paths,fp)
   requests.append(dict(bank=b['bank'],bank_index=b['bank_index'],direction=direction,bits=bits,driver_pin_centroid=P[0],sink_pin_centroid=P[1],driver_pin_span_bound_um=116/12 if direction=='outbound' else 119/12,sink_pin_span_bound_um=119/12 if direction=='outbound' else 116/12,stations=sl,raw_depth=dep[0],violations=bad,tiles_per_station=tiles,station_master_width=width,footprint_um2=fp))
   print(variant,b['bank'],direction,'depth',dep[0],'violations',len(bad),flush=True)
 maxima={d:max(r['raw_depth'] for r in requests if r['direction']==d) for d in ('outbound','return')}
 for r in requests:
  target=maxima[r['direction']];r['equal_age_depth']=target;r['padding_stations']=[]
  # Existing equal-age pad recipe: reserve every stage's real footprint at
  # the sink, never invent hidden valid-only holding state.
  for j in range(target-r['raw_depth']):
   xy,forced=RL.nearest_cap(router,cap,r['sink_pin_centroid'],r['footprint_um2']);cap.consume(int(xy[0]),int(xy[1]),r['footprint_um2'],forced=forced)
   r['padding_stations'].append(dict(depth=r['raw_depth']+j+1,x=(int(xy[0])+.5)*10,y=(int(xy[1])+.5)*10,master_width=r['station_master_width'],forced=bool(forced),tiles=r['tiles_per_station']))
 report=RL.window_report(router,cap)
 O=maxima['outbound'];R=maxima['return'];read=10+O+R;write=5+O
 return dict(variant=variant,status='CAPACITY_STATION_CONSTRUCTION_NOT_PLACED_OR_TIMING_QUALIFIED',source='0c55c33fc',outbound_edges=O,return_edges=R,requests=requests,capacity_forced=cap.forced,windows=report,derived_candidate_profile=dict(READ_SAMPLE=read,WRITE_COMMIT=write,SI=read+2,SS=2*read+2,WI=2*read+4,END=2*read+4+write,MIN_RELEASE=2*read+write+7,physical_ownership_tail=O+2,local_launch_to_calendar_zero=4),open=['GEN actual station-row legalization and every bit pin reach','propagated clock compensation on core, headers, selectors and stations','separate boot reset delivery','source parameter replay at derived profile','routed ownership status tail and producer retention calendar'])

if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__)
 for n in ('geometry','baseline','roots','clocks','grants','out'):a.add_argument('--'+n,required=True,type=Path)
 a.add_argument('--variant',choices=['MAIN','FB'],required=True);p=a.parse_args()
 d=run(*[load(getattr(p,n)) for n in ('geometry','baseline','roots','clocks','grants')],p.variant)
 d['input_sha256']={n:hashlib.sha256(getattr(p,n).read_bytes()).hexdigest() for n in ('geometry','baseline','roots','clocks','grants')}
 p.out.write_text(json.dumps(d,indent=1)+'\n');print('DONE',p.variant,d['outbound_edges'],d['return_edges'],d['capacity_forced'],flush=True)

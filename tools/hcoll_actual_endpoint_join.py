#!/usr/bin/env python3
"""Join exact closed controller pins to exact new-store CTS pins, all1180legs.
No source/clock/timing qualification is inferred from geometric reach.
"""
import argparse,hashlib,json,collections
from pathlib import Path
from hbm_system_geometry import lef
BASE=Path('/home/ubuntu/claude-takeover-20261007/hcoll_actual_join_inputs_1015')

def run(base):
 manifest=json.loads((base/'manifest.json').read_text())
 # Frozen sourcecopies are readonly; require every receipt hash to match.
 for p,r in manifest.items():
  path=base/('controller/'+Path(p).name if '/controller/' in p else Path(p).name)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('frozeninputchanged '+str(path))
 ctl=lef(base/'controller/ot_hgi_coll_static_capture_ctl.lef');store=json.loads((base/'south_cts_pin_geometry.json').read_text());ins=json.loads((base/'controller/insertion.json').read_text());ss={p['name']:p for p in store['pins'] if p['signal_type'] not in ('POWER','GROUND')};origins=[(0,236),(0,385.6),(227.36,236),(227.36,385.6)];cx,cy=55.36,0;legs=[];layers=collections.Counter()
 def source(name):
  # All signal controller pins in this source-bound view have a singleshape.
  return ctl['pins'][name]
 for b,(sx,sy) in enumerate(origins):
  for p,v in ss.items():
   if p=='clk':continue
   if p.startswith('din['):cp=f'bank_data[{b*141+int(p[4:-1])}]';kind='command'
   elif p.startswith('dout['):cp=f'stored[{b*141+int(p[5:-1])}]';kind='return'
   elif p=='we':cp='bank_we';kind='command'
   elif p.startswith('wa['):cp='bank_wa['+p[3:];kind='command'
   elif p.startswith('ra['):cp='bank_ra['+p[3:];kind='command'
   else:raise ValueError('unjoinedactualstoreport '+p)
   ax,ay=source(cp);dist=[]
   for shape in v['boxes']:
    x,y,X,Y=shape['rect_um'];bx=(x+X)/2+sx;by=(y+Y)/2+sy;dist.append((abs(cx+ax-bx)+abs(cy+ay-by),shape['layer'],bx,by))
   d,layer,bx,by=min(dist);layers[layer]+=1
   legs.append(dict(bank=b,kind=kind,controller_pin=cp,store_pin=p,controller_pin_xy_um=[cx+ax,cy+ay],store_pin_xy_um=[bx,by],store_layer=layer,manhattan_um=d))
 assert len(legs)==1180 and all(sum(e['bank']==b for e in legs)==295 for b in range(4))
 worst=max(legs,key=lambda e:e['manhattan_um']);budget=833.333333-60-150
 r=dict(schema='opentallas.hcoll.actual_controller_store_pin_join.v1',scope='closedcontrollerrealLEF +newstoreactualCTSODBpins; storestrictview/route/clockhold remainsUNQUALIFIED',source_manifest=manifest,controller_outline_um=ctl['size'],controller_origin_um=[cx,cy],store_origins_um=origins,composed_outline_um=[434.72,515.20],legs=legs,all_legs=1180,max_pin_manhattan_um=worst['manhattan_um'],worst=worst,over500_legs=sum(e['manhattan_um']>500 for e in legs),endpoint_store_layers=dict(layers),controller_actual_insertion=ins['tt']['boundary'],controller_actual_FF_insertion=ins['ff']['boundary'],controller_delivered_clock_phase='phi -318.2ps at its actual clockpin',store_clock_insertion=None,nominal_crosslevel_wire_plus_endpoint_budget_ps=budget,worst_wire_model_ps=.76*worst['manhattan_um'],worst_remaining_actual_launch_plus_capture_ps=budget-.76*worst['manhattan_um'],native_timing_qualified=False,store_adoption_hold=True,limits=['Actualgeometryonly, not pin-to-flop timing proof.','ControllermeanR318.2>300 requires earlier deliverytap and150ps conservative skew budget.','NewstoreactualR/spread andstrict native launch/capture absent; do not inherit oldNfaceview.','Layertransitions/vias,PG-aware channels,routedparasitics,holdandallclockdelivery remain required.','Sourcewordagesandallfixedcyclesunchanged; a geometry change alone doesnotprove those ages.'])
 r['per_bank']=[dict(bank=b,commands=max(e['manhattan_um'] for e in legs if e['bank']==b and e['kind']=='command'),returns=max(e['manhattan_um'] for e in legs if e['bank']==b and e['kind']=='return')) for b in range(4)]
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',default=str(BASE));p.add_argument('--out',required=True);a=p.parse_args();r=run(Path(a.inputs));Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['all_legs','max_pin_manhattan_um','over500_legs','worst','per_bank','endpoint_store_layers','worst_remaining_actual_launch_plus_capture_ps']}))
if __name__=='__main__':main()

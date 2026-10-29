#!/usr/bin/env python3
"""Actual-pin per-cut lower bound, independent of a particular FT jog location.
Every bit whose endpoints straddle a cut must cross it. Counts do not include
ordinary logic/clock/reset; exceeding capacity is structural, passing is only a
necessary condition. M6/M7 above M5 hard cores, <=0.6 track use, 64nm pitch.
"""
import argparse,json,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('out');ap.add_argument('--parts',required=True);ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools);import schema as S
from gen_phys import type_pins
P=S.Plan(json.loads((Path(a.geometry)/'die_plan.json').read_text()));out=[]
for pn in a.parts.split(','):
 tn=P.parts[pn]['type'];t=P.types[tn];pins={(n,i):(x,y) for n,i,_,x,y,_ in type_pins(P,tn)};events=[[],[]]
 for sl in t.get('ft_slots',[]):
  for bit in range(sl['width']+1):
   aa,bb=pins[sl['name']+'_i',bit],pins[sl['name']+'_o',bit]
   for axis in (0,1):
    lo,hi=sorted((aa[axis],bb[axis]))
    if hi-lo>1e-6:events[axis]+=[(lo,1,sl['name']),(hi,-1,sl['name'])]
 row=dict(part=pn,outline_um=t['outline_um'],scope='endpoint-straddling FT bits only; ordinary logic omitted')
 for axis,label in ((0,'M6_horizontal'),(1,'M7_vertical')):
  n=0;best=(0,0);active={};bestactive={}
  for x,delta,name in sorted(events[axis],key=lambda e:(e[0],e[1])):
   n+=delta;active[name]=active.get(name,0)+delta
   if n>best[0]:best=(n,x);bestactive={k:v for k,v in active.items() if v}
  supply=int(t['outline_um'][1-axis]/.064*.6);row[label]=dict(crossing_bits=best[0],coordinate_um=round(best[1],4),single_upper_layer_tracks_at60pct=supply,util=round(best[0]/max(supply,1),4),contributors=bestactive,verdict='FAIL_SINGLE_UPPER_LAYER_LOWER_BOUND' if best[0]>supply else 'NECESSARY_BOUND_ONLY_PASS')
 out.append(row)
Path(a.out).write_text(json.dumps(out,indent=1)+'\n')
for row in out:print(row['part'],row['M6_horizontal']['util'],row['M7_vertical']['util'])

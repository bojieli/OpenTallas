#!/usr/bin/env python3
"""Conservative PG/via-subtracted escape track inventory, not a routing verdict.
Input inventory.tcl TSV from the ACTUAL placed gate ODB. Output JSON.
A track crossing any PG shape/via anywhere in the allocated row corridor is
removed in full; unknown via layer span is conservatively all layers.
Signal-route/via access remains an independent trialroute+DRC obligation.
"""
import json,sys
from pathlib import Path
rows=[s.split('\t') for s in Path(sys.argv[1]).read_text().splitlines() if s]
dbu=float(next(r[1] for r in rows if r[0]=='DBU'))
tracks={};metal=[];vias=[];mac=[];layers={}
for r in rows:
 if r[0] in ('TRACKX','TRACKY'):tracks[r[0],r[1]]=[int(x)/dbu for x in r[2].split(',') if x]
 if r[0]=='LAYER':layers[r[1]]={'direction':r[2],'width':int(r[3])/dbu,'spacing':int(r[4])/dbu}
 if r[0]=='METAL':metal.append({'net':r[1],'layer':r[2],'box':[int(x)/dbu for x in r[3:7]]})
 if r[0]=='VIA':vias.append({'net':r[1],'name':r[2],'lo':int(r[3]),'hi':int(r[4]),'box':[int(x)/dbu for x in r[5:9]]})
 if r[0]=='MACRO':mac.append({'name':r[1],'master':r[2],'box':[int(x)/dbu for x in r[3:7]]})
def capacity(layer,box,axis):
 x0,y0,x1,y1=box;l=layers[layer];pad=l['spacing']+l['width']/2
 spans=[]
 for o in metal+vias:
  if 'layer' in o:
   if o['layer']!=layer:continue
  elif not o['lo']<=int(layer[1:])<=o['hi']:continue
  a,b,c,d=o['box'];a-=pad;b-=pad;c+=pad;d+=pad
  if c<x0 or a>x1 or d<y0 or b>y1:continue
  spans.append((a,c) if axis=='X' else (b,d))
 lo,hi=(x0,x1) if axis=='X' else (y0,y1)
 raw=[t for t in tracks['TRACK'+axis,layer] if lo<t<hi]
 free=[t for t in raw if not any(a<=t<=b for a,b in spans)]
 return {'raw_tracks':len(raw),'pg_via_blocked_tracks':len(raw)-len(free),'free_tracks_lower_bound':len(free),'free_track_coordinates_um':free}
report={'schema':'opentallas.s81_macro_escape_capacity.v1','inventory':sys.argv[1],'layers':layers,'PG_shape_count':len(metal),'PG_via_count':len(vias),'unknown_via_spans':sum(v['lo']==0 and v['hi']==99 for v in vias),'macros':mac,'rows':[],'qualification':'PG/via track-capacity evidence only; actual legal signal fanout, via access and trialroute/DRC required; no geometry approval implied'}
for m in mac:
 x0,y0,x1,y1=m['box']
 # Allocated escape corridors, explicitly inside the die and disjoint between
 # facing bottom macros.  The21.6um row spread is a plan, not a DRC verdict.
 for side,count,box in [('W',827,[max(5.4,x0-41.148),y0-21.6,x0,y1+21.6]),('E',825,[x1,y0-21.6,min(513,x1+41.148),y1+21.6])]:
  row={'macro':m['name'],'face':side,'corridor_um':box,'raw_face_pin_count':count,'raw_face_density_pins_per_um':count/81,'track_capacity':{}}
  for L in ('M3','M5'):row['track_capacity'][L]=capacity(L,box,'X')
  row['track_capacity']['M4']=capacity('M4',box,'Y')
  row['capacity_count_sufficient']=(sum(row['track_capacity'][L]['free_tracks_lower_bound'] for L in ('M3','M5'))>=count and row['track_capacity']['M4']['free_tracks_lower_bound']>=count)
  row['fanout_plan']='Native M4 stubs into face-specific41.148um channel, distinct M3/M5 vertical tracks and distinct M4 rows in124.2um allocation (21.6um spread each side). Requires obstacle-aware assignment, actualplaced logic and legal via/DRC. Count includes constant mask pins conservatively.'
  report['rows'].append(row)
Path(sys.argv[2]).write_text(json.dumps(report,indent=1)+'\n')
print('SH_ESCAPE_TRACK_INVENTORY faces',len(report['rows']),'sufficient_counts',[r['capacity_count_sufficient'] for r in report['rows']],'unknown_via_spans',report['unknown_via_spans'])

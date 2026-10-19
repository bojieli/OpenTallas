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
for a in sorted(mac,key=lambda m:(m['box'][1],m['box'][0])):
 for b in mac:
  if abs(a['box'][1]-b['box'][1])>.001 or a['box'][2]>=b['box'][0]:continue
  x0,x1=a['box'][2],b['box'][0];y0=a['box'][1]-22.668;y1=a['box'][3]+22.668;mid=(x0+x1)/2
  row={'left_macro':a['name'],'right_macro':b['name'],'corridor_um':[x0,y0,x1,y1],'macro_raw_face_pins':{'left_E':409,'right_W':410},'row_spread_pitch_um':86.4,'raw_face_density_pins_per_um':{'left_E':409/41.064,'right_W':410/41.064},'track_capacity':{}}
  for side,l,r in (('left_half',x0,mid),('right_half',mid,x1)):
   row['track_capacity'][side]={L:capacity(L,[l,y0,r,y1],'X') for L in ('M3','M5')}
  row['track_capacity']['horizontal_M4']=capacity('M4',[x0,y0,x1,y1],'Y')
  row['capacity_count_sufficient']=(sum(v['free_tracks_lower_bound'] for v in row['track_capacity']['left_half'].values())>=409 and sum(v['free_tracks_lower_bound'] for v in row['track_capacity']['right_half'].values())>=410 and row['track_capacity']['horizontal_M4']['free_tracks_lower_bound']>=819)
  row['fanout_plan']='Assign face pins monotonically to distinct free M3/M5 tracks in the corresponding half-channel; M4 stubs at native pin y, vertical turns to distinct M4 tracks in86.4um row allocation. Max nominal rowspread22.668um +halfchannel17.388um. Explicit obstacle-aware assignments and actual trialroute/DRC still required.'
  report['rows'].append(row)
report['all_faces']=[]
for m in mac:
 x0,y0,x1,y1=m['box']
 left=max(5.4,x0-37.8);right=min(297,x1+37.8)
 for n in mac:
  if abs(n['box'][1]-y0)>.001:continue
  if n['box'][2]<x0:left=max(left,(n['box'][2]+x0)/2)
  if n['box'][0]>x1:right=min(right,(x1+n['box'][0])/2)
 for side,count,a,b in [('W',410,left,x0),('E',409,x1,right)]:
  box=[a,y0-22.668,b,y1+22.668]
  cap={L:capacity(L,box,'X') for L in ('M3','M5')};cap['M4']=capacity('M4',box,'Y')
  report['all_faces'].append({'macro':m['name'],'face':side,'pins':count,'corridor_um':box,'capacity':cap,'count_sufficient':sum(cap[L]['free_tracks_lower_bound'] for L in ('M3','M5'))>=count and cap['M4']['free_tracks_lower_bound']>=count,'qualification':'Count only, native-pin stubs/obstacle-aware via assignment and actual trialroute/DRC remain required.'})
Path(sys.argv[2]).write_text(json.dumps(report,indent=1)+'\n')
print('ESCAPE_TRACK_INVENTORY rows',len(report['rows']),'sufficient_counts',[r['capacity_count_sufficient'] for r in report['rows']],'unknown_via_spans',report['unknown_via_spans'])

#!/usr/bin/env python3
"""Actual segment inventory and proposed native rectangles; no free-area claim."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
geometry=ROOT/'physical/hbm_accel_die_views/svc/svc_geometry.json'
segments=ROOT/'physical/hbm_accel_die_views/svc/seg_stages.json'
g=json.loads(geometry.read_text());s=json.loads(segments.read_text());rows=[]
for family,info in s['families'].items():
 for seg in info['segments']:
  pcs=sorted(int(re.fullmatch(r'pc(\d+)',u)[1])for u in seg['units']if re.fullmatch(r'pc(\d+)',u))
  rects=[]
  for pc in pcs:
   x=max(seg['x0'],g['hfd_svc_'+family]['pc_x'][pc]-94.824)
   for bank in range(2):rects.append({'PC':pc,'bank':bank,'rect_um':[x+bank*94.824,110,x+(bank+1)*94.824,151.04]})
  bounds=all(seg['x0']<=r['rect_um'][0] and r['rect_um'][2]<=seg['x1']for r in rects)
  overlap=any(a['rect_um'][0]<b['rect_um'][2] and b['rect_um'][0]<a['rect_um'][2]for i,a in enumerate(rects)for b in rects[i+1:])
  rows.append({'segment':seg['name'],'x0':seg['x0'],'x1':seg['x1'],'height_um':259.176,'PCs':pcs,'PC_count':len(pcs),
   'legacy_units':seg['units'],'legacy_placed_cell_area_um2':None,'codec_placed_cell_area_um2':None,
   'macro_rectangles':rects,'native_macro_area_um2':len(rects)*3891.57696,'native_rectangles_within_segment':bounds,
   'native_rectangles_nonoverlapping':not overlap,'loader_bottom_y_reservation_um':[0,100],
   'macro_y_separation_from_loader_um':10,'upper_codec_y_candidate_um':[151.04,230],
   'whole_band_fit':'UNPROVED_REQUIRES_LEGACY_CELL_OCCUPANCY_CODEC_AREA_AND_ROUTE_TRACKS'})
print(json.dumps({'schema':'opentallas.hbm_index_native_band_fit.v1','input_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [geometry,segments]},
 'geometry_scope':'native rectangles only; no proxy free-area approval; legacy inventory retained per actual segment',
 'segments':rows,'geometric_rectangles_fit':all(r['native_rectangles_within_segment']and r['native_rectangles_nonoverlapping']for r in rows),
 'physical_fit_qualified':False,'P_and_R_authorized_by_this_record':False},indent=2))

from pathlib import Path
import json,gzip,bisect,hashlib,re,collections
p=Path(__file__).parent;r=json.load(gzip.open(p/'d2d_actual_macro_escape_inventory.json.gz','rt'));u=r['dbu_per_um'];T=r['tracks']['M4'];ys=sorted({(a+i*s)/u for a,n,s in T['y_patterns_dbu'] for i in range(n)})
strips=[]
for row,y0 in enumerate([43.2,151.2]):
 for name,x0,x1,required in [('W',0,43.2,793),('middle',214.488,259.2,1585),('E',430.488,475.2,792)]:
  y1=y0+77.784;candidates=[y for y in ys if y0<=y<=y1];wireblocked=set();viaonly=set();shapecount=0
  for net,layer,kind,a,b,c,d in r['actual_pdn_routing_shapes']:
   if layer!='M4' or c<x0-.036 or a>x1+.036 or d<y0-.036 or b>y1+.036:continue
   shapecount+=1
   # .012 signal halfwidth +.024 minimum M4 spacing; this conservative
   # straight-through filter does NOT implement wide-metal/EOL/corner DRC.
   hits={y for y in candidates[bisect.bisect_left(candidates,b-.036):bisect.bisect_right(candidates,d+.036)]}
   (viaonly if kind=='actual_via_enclosure' else wireblocked).update(hits)
  blocked=wireblocked|viaonly
  strips.append(dict(name=f'row{row}_{name}',bounds_um=[x0,y0,x1,y1],width_um=round(x1-x0,6),raw_M4_tracks=len(candidates),raw_face_pin_demand=required,actual_PG_wire_blocked=len(wireblocked),additional_PG_via_enclosure_blocked=len(viaonly-wireblocked),remaining_conservative_straight_M4_tracks=len(candidates)-len(blocked),intersecting_PG_shapes=shapecount,qualification=False))
out=dict(schema='static-D2D-channel-PG-track-characterization',route_proof=False,literal_raw_pin_density='FAIL',db_sha256=Path(p/'native_final_remote_sha256.txt').read_text().splitlines()[0],actual_M4_track_pitch_um=.048,signal_halfwidth_plus_minspacing_um=.036,scope='Conservative straight-through M4 track filtering against actual expanded PG via enclosures/wires, no data wires. NOT a legal escape capacity or DRC proof; wide-metal/EOL/corner rules and M3/M5 transitions unmodeled. Opposing pins need not cross whole strip, so raw-demand comparisons cannot prove route infeasibility either.',strips=strips)
(p/'d2d_static_escape_track_model.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

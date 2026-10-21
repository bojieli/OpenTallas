#!/usr/bin/env python3
"""Bounded required HEAD lane placement model. Exclusions are not waived by this model."""
import json,math,subprocess,sys
from pathlib import Path
def read_spec(path):
 if ':' in path:
  return json.loads(subprocess.check_output(['git','show',path],text=True))
 return json.loads(Path(path).read_text())
endpoint_arg,lane_arg,out_arg=sys.argv[1:4]
x={'endpoint':read_spec(endpoint_arg),'lane':read_spec(lane_arg)};e=x['endpoint'];l=x['lane'];er=e['pin_ranges'];lr=l['pin_ranges'];H=l['outline']['h'];W=l['outline']['w'];gap=17.28;grid=2.16;core_y=345.6;prev=-1e9;rows=[]
for i in range(4):
 links=[(f'lo{i}_d','li_d'),(f'lo{i}_v','li_v'),(f'lo{i}_r','li_r'),(f'li{i}_d','lo_d'),(f'li{i}_v','lo_v'),(f'li{i}_r','lo_r'),(f'l{i}_f','flt')]
 lo,hi=0,2592-H
 for a,b in links:
  ca,cb=er[a];la,lb=H-lr[b][1],H-lr[b][0];vlim=405-gap
  lo=max(lo,core_y+cb-la-vlim);hi=min(hi,core_y+ca-lb+vlim)
 y=round(math.ceil((max(lo,prev+H+grid)-1e-7)/grid)*grid,6)
 assert y<=hi,(i,lo,hi,y)
 measured=[]
 for a,b in links:
  cy=[core_y+z for z in er[a]];ly=[y+H-z for z in lr[b]];reach=gap+max(abs(c-d) for c in cy for d in ly);assert reach<=405.00001
  measured.append(dict(core_port=a,lane_port=b,max_window_to_window_um=round(reach,3)))
 rows.append(dict(lane=i,x=43.2,y=y,w=W,h=H,orientation='MX',y_feasible=[round(lo,3),round(hi,3)],max_hop_um=max(q['max_window_to_window_um'] for q in measured),ports=measured));prev=y
out={'status':'PARTIAL_PLANNED_PIN_MODEL_NOT_CLOSED','source':{'endpoint_spec':endpoint_arg,'lane_spec':lane_arg,'note':'No aliases of physical views'},'reserve':[2592,2592],'endpoint':{'x':round(43.2+W+gap,3),'y':core_y,'w':561.6,'h':1900.8,'orientation':'R0'},'lane_to_core_gap_um':gap,'method':'Every corner of each full declared base-port window, stronger than one-to-one bit pairing; MX transforms lane Eface; all rectangles have >=2.16um separation. Actual closed LEF pins, PG, access, congestion and CTS remain authoritative.','lanes':rows,'max_data_control_window_hop_um':max(q['max_hop_um'] for q in rows),'excluded_owed':['rxv/rxvb startup-enable flops reach opposite W lane RX[0] face (>725um), requires real source disposition','actual ML E2/land placement bound ecdd507d1 must be instantiated and reprojected','actual macro routing/channel/clock closure; this pin model does not qualify physical fit']}
out['orientation_status']='UNQUALIFIED until actual exported CRED12 LEF passes check_macro_track_alignment at all placements; source2.16um lattice alone is insufficient'
out['corridor_status']='17.28um horizontal/min2.16um vertical are geometric candidates only, not clock/data/PG/cell route qualification; enlarge legal reserve if actual access requires it'
Path(out_arg).write_text(json.dumps(out,indent=2)+'\n');print([(q['lane'],q['y'],q['max_hop_um']) for q in rows],out['max_data_control_window_hop_um'])

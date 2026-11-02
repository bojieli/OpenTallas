import json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;n=runpy.run_path(str(O/'solve_launch_regions.py'));D=n['D'];G=n['G'];a=n['anchors'];caps=n['captures'];bad=[];peak=None;edges=0
for src,ps in a.items():
 for dst in caps(src):
  if dst not in a:continue
  edges+=1
  for p in ps:
   for q in a[dst]:
    d=abs(p['x']-q['x'])+abs(p['y']-q['y'])
    r=dict(port_L1_um=d,minimum_FF_L1_lower_bound_um=d-300,source_FF=D.cells[src][6],capture_FF=D.cells[dst][6],source_pin=p,capture_pin=q)
    if peak is None or d>peak['port_L1_um']:peak=r
    if d>705+1e-6:bad.append(r)
x=dict(public_edges=edges,over705=len(bad),worst=peak,witnesses=sorted(bad,key=lambda x:-x['port_L1_um']))
(O/'public_edge_witness.json').write_text(json.dumps(x,indent=2)+'\n');print('PUBLICEDGE',edges,len(bad),peak)

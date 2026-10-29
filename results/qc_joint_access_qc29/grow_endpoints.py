#!/usr/bin/env python3
"""DIE-QC-29: apply a growth candidate (type-uniform tap_pin_heights_um) to native endpoint M7 rects, centre fixed."""
import json,sys
ep_path,growth,out=sys.argv[1:4]
e=json.load(open(ep_path));wrap="endpoints" in e;E=e.get("endpoints",e)
g=json.load(open(growth));n=0
for r in g["impacted_pins"]:
    q=E[r["port"]];x0,y0,x1,y1=q["rect_um"];cy=(y0+y1)/2;h=r["proposed_height_um"]
    q["rect_um"]=[x0,round(cy-h/2,6),x1,round(cy+h/2,6)];n+=1
json.dump(e,open(out,"w"));print("GROWN",n,"of",len(E))

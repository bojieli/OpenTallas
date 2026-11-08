import sys,json,re
sys.path[:0]=["tools/die_plan","physical/die_plan/s81"]
import schema, taps
from pathlib import Path
P=schema.Plan(json.load(open(sys.argv[1])),Path(sys.argv[1]))
bad=[]
for tn in sorted(P.types):
    if not re.match(r"^ot_s81sl_leaf__t\d+",tn): continue
    if P.types[tn].get("clock",{}).get("tap_mode")!="grid+explicit": continue
    try: taps.grid_explicit_taps(P,tn)
    except Exception as e: bad.append((tn,str(e)[:160]))
print(len(bad)); [print(b) for b in bad]

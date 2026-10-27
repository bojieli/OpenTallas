"""QUAD-8: pretree compact clk_ctl = the actual BPin centre (82.104,120.984) M5 (Codex ODB query; GEOM-28 PASS entry), not the stale E-edge 164.141."""
import json,sys
from pathlib import Path
f=Path(sys.argv[1])/"cores/ot_hbm_su_static_pgslice_lg__pretree__164.16x241.92__content_trial.json"
p=json.loads(f.read_text()); n=0
for q in p:
    if q.get("name")=="clk_ctl": print("old",q); q.update(layer="M5",x=82.104,y=120.984); n+=1
f.write_text(json.dumps(p,indent=1)+"\n"); print("clk_ctl set",n)

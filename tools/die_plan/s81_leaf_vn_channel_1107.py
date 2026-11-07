#!/usr/bin/env python3
"""t27 vM successor: widen the vn/VP pin-access channel; no RTL or plan change."""
import argparse, hashlib, json, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("kit",type=Path);p.add_argument("--apply",action="store_true");a=p.parse_args()
f=a.kit/"macro_place.tcl";s=f.read_text();before=hashlib.sha256(s.encode()).hexdigest();moves=[]
for name,y in [("u_bound.u_u_lf0_u_vn_u_a",699.852),("u_bound.u_u_lf0_u_vn_u_b",881.292)]:
 pat=re.compile(r"(place_macro -macro_name \{"+re.escape(name)+r"\} -location \{)([\d.]+) ([\d.]+)(\})")
 m=pat.search(s);assert m,name
 x0,y0=float(m[2]),float(m[3]);assert abs(x0-535.812)<0.001 and abs(y0-y)<0.001,(name,x0,y0)
 x=x0-25.92;s=pat.sub(lambda m:m[1]+f"{x:.4f} {y0:.4f}"+m[4],s,count=1);moves.append({"instance":name,"old_um":[x0,y0],"new_um":[x,y0]})
# Original east edge892.212 vs nearest VP macro907.308. The move keeps the west channel above34um.
result={"schema":"opentallas.kit_profile.v1","profile":"s81_leaf_vn_channel_1107","source_macro_sha256":before,"result_macro_sha256":hashlib.sha256(s.encode()).hexdigest(),"moves":moves,"channel_um":{"before":15.096,"after":41.016,"west_min_after":34.56},"pin_cycles_added":0,"rtl_changed":False,"plan_changed":False,"goal":"place only; review before GRT"}
print(json.dumps(result,indent=2))
if a.apply:f.write_text(s);(a.kit/"SOURCE_PROFILE.json").write_text(json.dumps(result,indent=2)+"\n")

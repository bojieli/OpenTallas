#!/usr/bin/env python3
"""QC-PG-2: su8_superpose.py (Codex 4fc469ac5c) with separate A0 (A) and flattened (F) background densities.
Usage: su8_superpose2.py KITROOT CORES_JSON SU8_W BG_A BG_F [window: su8|all]"""
import csv,json,re,sys
from pathlib import Path
base=Path(sys.argv[1]); cores=json.loads(Path(sys.argv[2]).read_text())["cores"]
power,bgA,bgF=map(float,sys.argv[3:6]); win=sys.argv[6] if len(sys.argv)>6 else "su8"
scale=power/.0337; raw={}
for cls in ("S","U8","A","F"):
    d=base/cls/"M9w672_p70_SU"/"psm"; raw[cls]={}
    for net in ("VDD","VSS"):
        vals={}
        for row in csv.DictReader((d/f"ir_{net}.csv").open()):
            v=float(row["Voltage"]); mv=(v if net=="VSS" else .7-v)*1000
            k=row["Instance"]; vals[k]=max(vals.get(k,-1e9),mv)
        raw[cls][net]=vals
d=base/"S"/"M9w672_p70_SU"/"psm"
s=(d/"psm.tcl").read_text()
pl={m[1]:(float(m[2]),float(m[3])) for m in re.finditer(r"^ot_pl (\S+) (\S+) (\S+)",s,re.M)}
size=float(re.search(r"SIZE (\S+) BY",(d/"irblk.lef").read_text())[1])
width=max(x for x,y in pl.values())+size
su=[c for c in cores if c["module"]=="qfd_dv_s5_su8_rst3"]
values=[]
for k,(x,y) in pl.items():
    cx,cy=x+size/2,y+size/2
    if not(450<=cx<=width-450 and 450<=cy<=width-450):continue
    gx,gy=cx+26352,cy+9504
    insu=any(c["rect"][0]<=gx<=c["rect"][2] and c["rect"][1]<=gy<=c["rect"][3] for c in su)
    if win=="su8" and not insu:continue
    if win=="nosu8" and insu:continue
    up={n:raw["S"][n][k]+(scale-1)*raw["U8"][n][k]+bgA*raw["A"][n][k]+bgF*raw["F"][n][k] for n in ("VDD","VSS")}
    parts={c:sum(raw[c][n][k] for n in ("VDD","VSS")) for c in ("S","U8","A","F")}
    values.append((up["VDD"]+up["VSS"],k,up,parts))
upper,node,up,parts=max(values,key=lambda t:t[0])
print(json.dumps(dict(window=win,su8_W=power,bgA=bgA,bgF=bgF,upper_mV=round(upper,3),VDD=round(up["VDD"],3),VSS=round(up["VSS"],3),node=node,
  unit_responses_mV=parts,below_mV_retained=6.602,total_mV=round(upper+6.602,3))))

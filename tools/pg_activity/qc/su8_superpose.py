#!/usr/bin/env python3
"""Reuse QC-PG-MAP linear class solves; scale SU8 only, retain below-grid bound.
Outputs INFO: class responses preserve uniform load over each core outline.
Usage: su8_superpose.py KITROOT CORES_JSON SU8_W BACKGROUND_W_MM2
"""
import csv,json,re,sys
from pathlib import Path
base=Path(sys.argv[1]); cores=json.loads(Path(sys.argv[2]).read_text())["cores"]
power,bg=map(float,sys.argv[3:5]); scale=power/.0337; raw={}
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
    if not any(c["rect"][0]<=gx<=c["rect"][2] and c["rect"][1]<=gy<=c["rect"][3] for c in su):continue
    upper=sum(raw["S"][n][k]+(scale-1)*raw["U8"][n][k]+bg*(raw["A"][n][k]+raw["F"][n][k]) for n in ("VDD","VSS"))
    values.append((upper,k))
upper,node=max(values)
print(json.dumps(dict(su8_W=power,background_W_mm2=bg,upper_mV=upper,below_mV_retained=6.602,total_mV=upper+6.602,node=node,
    scope="INFO uniform current over each core outline; below-M7 bound retained, not scaled from total power")))

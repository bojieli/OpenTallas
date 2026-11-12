import json,sys,re,collections
D=json.load(open(sys.argv[1])); H0,H1=345.6,483.84; dH=round(H1-H0,3)
W=197.856
def side(d):
    if "w" in d: return "BOX"
    if d["x"]<0.5: return "W"
    if d["x"]>W-0.6: return "E"
    if d["y"]<0.5: return "S"
    if d["y"]>H0-0.6: return "N"
    return "IN"
bus=lambda n: re.sub(r"\[\d+\]$","",n)
Wp=[d for d in D if side(d)=="W"]
# contiguous runs by bus ordered by y
order=sorted(Wp,key=lambda d:d["y"])
runs=[];
for d in order:
    if runs and runs[-1][0]==bus(d["name"]): runs[-1][1].append(d)
    else: runs.append([bus(d["name"]),[d]])
n=len(runs); print("W runs",n)
# distribute extra dH as uniform gaps between runs, snapped to 0.864
step=dH/(n)  # gap after each run incl. top margin share
shift=0.0
import math
for i,(b,ds) in enumerate(runs):
    s=round(round(i*dH/n/0.864)*0.864,3)
    for d in ds: d["y"]=round(d["y"]+s,3)
for d in D:
    sd=side(d)
    if sd=="N": d["y"]=round(d["y"]+dH,3)
    elif sd=="E" and d["y"]>1: d["y"]=round(d["y"]+round(dH/2/0.864)*0.864,3)
json.dump(D,open(sys.argv[2],"w"),separators=(",",":"))
ys=[d["y"] for d in D if side(d)=="W" or True]
print("max y",max(d["y"] for d in D), "W y range",min(d["y"] for d in Wp),max(d["y"] for d in Wp))
# sanity: unique (side,layer,coord)
c=collections.Counter((side(d),d["layer"],d["x"],d["y"]) for d in D); print("dups",sum(1 for v in c.values() if v>1))

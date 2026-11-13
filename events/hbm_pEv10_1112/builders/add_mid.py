# add_mid.py IN OUT TYPE:SLOT N : +N stations on a regs-only ft slot (no bit_sites_um), each at the midpoint
# (vertical-then-horizontal corner kept Manhattan: midpoint of the longest consecutive reg->reg hop).
import json,sys
src,out,ts,n=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])
d=json.load(open(src)); tn,sn=ts.split(":")
s=next(x for x in d["partition_types"][tn]["ft_slots"] if x["name"]==sn)
assert not s.get("bit_sites_um"), "slot has bit sites; use ft_add_station"
r=s["regs_um"]; assert len(r)==int(s["stations"])
for _ in range(n):
    i=max(range(len(r)-1),key=lambda k:abs(r[k][0]-r[k+1][0])+abs(r[k][1]-r[k+1][1]))
    a,b=r[i],r[i+1]; m=[round((a[0]+b[0])/2/0.216)*0.216,round((a[1]+b[1])/2/0.27)*0.27]
    r.insert(i+1,[round(m[0],3),round(m[1],3)])
    print(f"{ts}: insert at {i+1} {r[i+1]} hop {abs(a[0]-b[0])+abs(a[1]-b[1]):.1f}")
s["stations"]=len(r); s["note"]=(s.get("note","")+f" | DIE-HBM-101 11-12 pEv6: +{n} mid station(s) (q_sm0 NW/NE landing symmetry, bindEv4 TYPE_SPLIT)").strip(" |")
json.dump(d,open(out,"w"))

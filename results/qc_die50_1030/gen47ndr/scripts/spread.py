import json,sys,collections
a=json.load(open(sys.argv[1]))
kit={}
for ln in open(sys.argv[2]):
    f=ln.split()
    if f and f[0]=="T": kit[f[1]]=float(f[2])
reg=collections.defaultdict(list)
for t in a["taps"]: reg[t["cppr_node"]].append(t)
rows=[]
for r,ts in reg.items():
    L=[t["late_ps"] for t in ts]; K=[kit[t["port"]] for t in ts]
    rows.append((max(L)-min(L), max(K)-min(K), r, len(ts)))
rows.sort(reverse=True)
print("regions",len(rows),"routed spread>150:",sum(1 for x in rows if x[0]>150),"kit(placement) spread>150:",sum(1 for x in rows if x[1]>150))
for x in rows[:12]: print("%-14s n=%4d routed %.1f kit %.1f"%(x[2],x[3],x[0],x[1]))
import statistics
d=[t["late_ps"]-kit[t["port"]] for t in a["taps"]]
print("routed-kit late delta: median %.1f min %.1f max %.1f"%(statistics.median(d),min(d),max(d)))
print("tap slew max %.1f"%max(t["slew_ps"] for t in a["taps"]))
w=reg["c_E1_bn_11"]; w.sort(key=lambda t:t["late_ps"])
for t in w[:3]+w[-3:]: print(t["port"],round(t["late_ps"],1),round(kit[t["port"]],1),t["stages_from_root"],t["xy_um"])

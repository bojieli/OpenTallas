import json,statistics as st,sys
B=sys.argv[1]
m=json.load(open(B+"/mesh.json")); band={t["port"]:t for t in m["taps"] if t.get("band_tree")}
for C in ("TT","FF"):
    a={};sl={}
    for l in open(f"{B}/taps_{C}.txt"):
        f=l.split()
        if f and f[0]=="T": a[f[1]]=float(f[2]); sl[f[1]]=float(f[4])
    bb=[v for k,v in a.items() if k in band]; mm=[v for k,v in a.items() if k not in band]
    print(B,C,"band-mesh median %.2f"%(st.median(bb)-st.median(mm)),"window %.1f-%.1f"%(min(a.values()),max(a.values())),"band %.1f-%.1f"%(min(bb),max(bb)),"mesh %.1f-%.1f"%(min(mm),max(mm)),"slew>120",[(k,round(sl[k],1),band.get(k,{}).get("stub_um")) for k in sl if sl[k]>120])

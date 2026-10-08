import json,csv,glob,sys
for d in sys.argv[1:]:
    m=json.load(open(d+"/manifest.json")); w=m["window_um"]; j=m["judged_um"]; vdd=m.get('vdd_v',0.7)
    def rd(n):
        return {r["Instance"]:(float(r["X location"]),float(r["Y location"]),float(r["Voltage"])) for r in csv.DictReader(open(f"{d}/ir_{n}.rpt"))}
    vd,vs=rd("VDD"),rd("VSS")
    best=(0,None,0,0); raw=(0,None)
    for k,(x,y,v) in vd.items():
        r2r=(vdd-v)+vs[k][2]; X,Y=w[0]+x,w[1]+y
        if r2r>raw[0]: raw=(r2r,(round(X),round(Y)))
        if j[0]<=X<=j[2] and j[1]<=Y<=j[3] and r2r>best[0]: best=(r2r,(round(X),round(Y)),vdd-v,vs[k][2])
    print(d.split('/')[-1], "power_W=%.2f"%m['power_w'], "raw_r2r_mV=%.2f@%s"%(raw[0]*1e3,raw[1]), "judged_r2r_mV=%.2f@%s (VDD %.2f + VSS %.2f)"%(best[0]*1e3,best[1],best[2]*1e3,best[3]*1e3), "judged", [round(v) for v in j])

import sys,json,time
S,base,cand,tn=sys.argv[1:5]
sys.path.insert(0,S+"/tools/die_plan")
import schema
t0=time.time()
rc=json.load(open(cand))
errs=schema.validate(rc)
print("validate errors:",len(errs) if errs else 0, (errs or [])[:5], round(time.time()-t0))
Pb=schema.Plan(json.load(open(base))); Pc=schema.Plan(rc)
print("plan load ok", round(time.time()-t0))
# lanes touching this type
ch=[]
for lid in Pc.lanes:
    try:
        a=Pb.lane_latency(lid); b=Pc.lane_latency(lid)
    except Exception as e:
        ch.append((lid,"ERR",str(e)[:200])); continue
    if a!=b: ch.append((lid,a.get("cycles"),b.get("cycles")))
print("lanes changed:",len(ch))
for r in ch[:60]: print(r)

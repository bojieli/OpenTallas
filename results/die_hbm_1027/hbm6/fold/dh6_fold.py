import sys,json
sys.path[:0]=["tools","tools/throughput"]
import accepted_cost as A
run,count=A.hbm_schedule("ds")
from hgi_sim import timing as T
CLK=1.2e9
base=run(); print("base cycles",base,"tok/s",CLK/base)
out=dict(base=base)
for op,d in (("SU.*",1),("SU.*",2),("SM.*",1),("DMA.*",1),("COLL.*",1)):
  c=run(op,1.0,d); out[f"{op}+{d}"]=c; print(op,"+%d"%d,c,"tok/s %.1f"%(CLK/c),"loss %.2f%%"%(100*(c/base-1)))
fp=T.CAL.setdefault("floorplan",{})
old=fp.get("su_lanes")
for n in (256,):
  fp["su_lanes"]=dict(value=n); c=run(); out[f"su_lanes{n}"]=c; print("su_lanes",n,c,"tok/s %.1f"%(CLK/c),"loss %.2f%%"%(100*(c/base-1)))
fp["su_lanes"]=old
for op in ("SU.*","SM.*","DMA.*","COLL.*"):
  c=run(op,2.0,0); out[f"{op}x2"]=c; print(op,"x2",c,"tok/s %.1f"%(CLK/c),"loss %.2f%%"%(100*(c/base-1)))
json.dump(out,open("/tmp/dh6_fold.json","w"),indent=1)

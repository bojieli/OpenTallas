# hd_host_w spread v2: all origins on the 8.64-um lattice; rows paired (25.92 inside a pair, 34.56 between pairs)
import json,sys,hashlib
sys.path.insert(0,sys.argv[3]+"/tools/die_plan")
import reset_tree as R
src,dst=sys.argv[1],sys.argv[2]
p=json.load(open(src)); t=p["partition_types"]["hd_host_w"]
X0,PX,NX0=77.76,51.84,float(sys.argv[4]); NPX=float(sys.argv[5]) if len(sys.argv)>5 else 95.04
Y0,PY,NY0=120.96,25.92,51.84
d={}
for h in t["hard_cores"]:
    x,y=h["origin_um"]; i=round((x-X0)/PX); j=round((y-Y0)/PY)
    assert abs(X0+i*PX-x)<1e-3 and abs(Y0+j*PY-y)<1e-3
    nx=round(NX0+i*NPX,3); ny=round(NY0+(j//2)*60.48+(j%2)*25.92,3)
    assert abs(nx/8.64-round(nx/8.64))<1e-6 and abs(ny/8.64-round(ny/8.64))<1e-6,(nx,ny)
    d[h["inst"]]=[[x,y],[nx,ny]]; h["origin_um"]=[nx,ny]
W,H=t["outline_um"]
print("outline",W,H,"xmax",max(v[1][0] for v in d.values())+32,"ymax",max(v[1][1] for v in d.values())+17.3)
print("core outline sample",t["hard_cores"][0].get("outline_um"),t["hard_cores"][0].get("orient"))
boxes=R.blockages(t); box=(R.CLEAR_UM,R.CLEAR_UM,W-R.CLEAR_UM,H-R.CLEAR_UM)
for xy in t["reset"]["local_taps_um"]+[t["clock"]["tap_um"]]:
    hit=[b for b in boxes if b[0]<xy[0]<b[2] and b[1]<xy[1]<b[3]]
    print("tap",xy,"free" if R._free(tuple(xy),boxes,box) else "BLOCKED",hit[:2])
json.dump(p,open(dst,"w"),indent=1)
json.dump({"hd_host_w":{k:v[1]+[None] for k,v in d.items()}},open(dst+".delta.json","w"),indent=1)
print(hashlib.sha256(open(dst,"rb").read()).hexdigest())

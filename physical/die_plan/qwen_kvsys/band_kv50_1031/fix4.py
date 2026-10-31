# DIE-KV-50: bands whose ring_ff re-site adds a G0C geom WARN instead grow IN PLACE (resized_from_um) to 1.35x the old
# area = the measured CA-ring need (AUTOBUILD-PIPE-3: 1.29-1.30x), along the long axis, direction chosen free of
# other bands, type blockages and die islands.
import json,sys,copy
sys.path.insert(0,"tools/die_plan")
import clock_landing_plan as C
plan_p,out_p=sys.argv[1:3]; keys=sys.argv[3].split(",")
raw=json.load(open(plan_p))
for key in keys:
    tn,bus=key.split("/"); t=raw["partition_types"][tn]; bands=t["clock"]["landing_contract"]["bands"]; b=bands[bus]
    x0,y0,x1,y1=b["resized_from_um"]; w,h=x1-x0,y1-y0; W,H=t["outline_um"]
    obst=[list(o["rect_um"]) for k,o in bands.items() if k!=bus and o.get("rect_um")]+C.RT.blockages(t)+[list(r) for r in (t.get("clock") or {}).get("die_islands_um",[])]
    nh=-(-(1.35*h)//2.16)*2.16; nw=-(-(1.35*w)//0.216)*0.216
    ya=[[x0,y0,x1,y0+nh],[x0,y1-nh,x1,y1]]; xa=[[x0,y0,x0+nw,y1],[x1-nw,y0,x1,y1]]
    cands=ya+xa if h>=w else xa+ya     # long axis first, then the short axis
    ok=[c for c in cands if c[0]>=4.32-1e-6 and c[1]>=4.32-1e-6 and c[2]<=W-4.32+1e-6 and c[3]<=H-4.32+1e-6 and not any(C._rect_overlap(c,o) for o in obst)]
    if not ok: print("FIX4 NOFIT",tn,bus,cands); sys.exit(2)
    c=[round(v,4) for v in ok[0]]
    nb=dict(b); nb["rect_um"]=c; nb["area_reserve_um2"]=round((c[2]-c[0])*(c[3]-c[1]),2)
    nb["resize"]="DIE-KV-50 in-place grow 1.35x (measured CA-ring need 1.29-1.30x; the ring_ff re-site added a G0C geom WARN)"
    print("FIX4",tn,bus,b["resized_from_um"],"->",c, round((c[2]-c[0])*(c[3]-c[1]),1),"um2")
    bands[bus]=nb
open(out_p,"w").write(json.dumps(raw,indent=1,ensure_ascii=False)+"\n")

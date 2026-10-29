import json,sys
p=json.load(open(sys.argv[1]))
H=4.32;G=4.32
cands={"sfustore_hw":[("A",561.6,276.48),("B",483.84,267.84),("C",475.2,241.92)],
 "vmdel_lane_n":[("A",257.04,108.0),("Bp",142.56,116.64)],
 "pslice_c5":[("grow",1080.0,864.0),("half",475.2,760.32)],
 "qcore_r13":[("A",267.84,250.56),("B",293.76,233.28)]}
R=int(sys.argv[2]) if len(sys.argv)>2 else 60
for t in ["q_hub_nw","q_hub_ne"]:
  pt=p["partition_types"][t]; W,Hh=pt["outline_um"]
  rects=[(hc["inst"],hc["module"],hc["origin_um"][0],hc["origin_um"][1],hc["outline_um"][0],hc["outline_um"][1]) for hc in pt["hard_cores"]]
  for key,cl in cands.items():
    for (i,m,x,y,w,h) in rects:
      if key not in m: continue
      cx,cy=x+w/2,y+h/2; out=[]
      for lab,nw,nh in cl:
        best=None
        for dx in range(-R,R+1):
          for dy in range(-R,R+1):
            nx=x+dx*G; ny=y+dy*G
            # candidate must overlap original footprint region (keep locality): measure centre shift
            if nx<0 or ny<0 or nx+nw>W or ny+nh>Hh: continue
            d=abs(nx+nw/2-cx)+abs(ny+nh/2-cy)
            if best and d>=best[0]: continue
            ok=True
            for (j,m2,x2,y2,w2,h2) in rects:
              if j==i: continue
              if nx < x2+w2+H and x2 < nx+nw+H and ny < y2+h2+H and y2 < ny+nh+H: ok=False;break
            if ok: best=(d,nx,ny)
        out.append(f"{lab}:"+(f"shift{best[0]:.0f}um" if best else f"NOFIT<{R*G:.0f}"))
      print(t,i,m[-22:]," ".join(out))

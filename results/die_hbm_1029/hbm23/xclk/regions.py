import sys,numpy as np
# xcal macro geometry (macro_placement.tcl + LEF sizes): prog_hi y 8.65-79.14 x 33.59-208.33; prog_lo y 142.28-212.77; tab_lo x 20.16-114.98 y 90.16-131.22; tab_hi x 131.98-226.80
R={"NW":(0,33.59,131.22,224.64),"WM":(0,20.16,90.16,131.22),"SW":(0,33.59,0,90.16),
   "NE":(208.33,241.92,131.22,224.64),"EM":(226.8,241.92,90.16,131.22),"SE":(208.33,241.92,0,90.16),
   "CN":(33.59,208.33,131.22,142.28),"CS":(33.59,208.33,79.14,90.16),"CG":(114.98,131.98,90.16,131.22),
   "TOP":(33.59,208.33,212.77,224.64),"BOT":(33.59,208.33,0,8.65)}
ins={};ff={}
for fn,d in ((sys.argv[1],ins),(sys.argv[2],ff)):
    for l in open(fn):
        if l[0]=="#": continue
        p=l.split(); d[p[0]]=(float(p[1]),float(p[2]),float(p[3]))
ex,ey=125.304,125.28
print("region n  centroid(x,y)  maxdist_from_centroid  dist_entry->centroid  TT p50/max  FF max")
for k,(x0,x1,y0,y1) in R.items():
    s=[(n,v) for n,v in ins.items() if x0<=v[1]<x1 and y0<=v[2]<y1]
    if not s: print(k,0); continue
    xs=np.array([v[1] for n,v in s]); ys=np.array([v[2] for n,v in s]); a=np.array([v[0] for n,v in s]); f=np.array([ff[n][0] for n,v in s])
    cx,cy=np.median(xs),np.median(ys); dm=np.max(np.abs(xs-cx)+np.abs(ys-cy))
    print("%-4s %4d (%6.1f,%6.1f) %6.0f %6.0f   %5.0f/%5.0f  %5.0f"%(k,len(s),cx,cy,dm,abs(cx-ex)+abs(cy-ey),np.median(a),a.max(),f.max()))
print("unassigned",len(ins)-sum(1 for n,v in ins.items() if any(x0<=v[1]<x1 and y0<=v[2]<y1 for x0,x1,y0,y1 in R.values())))

# HEAD-KITS-10 estimate: ft slot route length L (face_flops zroute, bit-median) and hop lengths
import json,sys,os,statistics as st
R=sys.argv[1]
def zroute(ax,ay,bx,by,fin,fout):
    if abs(ax-bx)<1 or abs(ay-by)<1: return abs(ax-bx)+abs(ay-by)
    return abs(ax-bx)+abs(ay-by)  # L / Z manhattan length is the same
print("type\tslot\tk\tin\tout\tbits\tL_med\tL_max\thop_now(L/k)\thop_face(L/(k-1))\tk_need(face,<=405)")
for t in sorted(os.listdir(R)):
    f=f"{R}/{t}/ft_stations.txt"
    if not os.path.exists(f): continue
    pins=json.load(open(f"{R}/{t}/pins.json"))
    P={(p['bus'],p['bit']):p for p in pins}
    for ln in open(f):
        if ln.startswith('#') or not ln.strip(): continue
        s,k,fi,fo=ln.split()[:4]; k=int(k)
        Ls=[]
        for (b,i),p in P.items():
            if b==s+'_i' and (s+'_o',i) in P:
                q=P[(s+'_o',i)]; Ls.append(zroute(p['x'],p['y'],q['x'],q['y'],fi,fo))
        if not Ls: print(t,s,"nopins"); continue
        Lm=st.median(Ls); Lx=max(Ls)
        import math
        kn=math.ceil(Lx/405)+1
        print(f"{t}\t{s}\t{k}\t{fi}\t{fo}\t{len(Ls)}\t{Lm:.0f}\t{Lx:.0f}\t{Lx/k:.0f}\t{(Lx/(k-1) if k>1 else float('inf')):.0f}\t{kn}")

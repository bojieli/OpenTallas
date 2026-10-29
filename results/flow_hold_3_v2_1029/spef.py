import sys,re
want=set(sys.argv[2].split(","))
f=open(sys.argv[1]); names={}; cur=None; mode=None; res={}
for l in f:
    if l.startswith("*NAME_MAP"): mode="map"; continue
    if mode=="map":
        if l.startswith("*"):
            m=re.match(r"\*(\d+)\s+(\S+)",l)
            if m: names["*"+m.group(1)]=m.group(2).replace("\\","")
            elif l.startswith("*PORTS") or l.startswith("*D_NET"): mode=None
        else: mode=None if l.strip()=="" and False else mode
    if l.startswith("*D_NET"):
        p=l.split(); n=names.get(p[1],p[1]); cur=n if n in want else None
        if cur: res[cur]=[float(p[2]),0.0,0]; sec=None
        continue
    if cur:
        if l.startswith("*CAP"): sec="c"; continue
        if l.startswith("*RES"): sec="r"; continue
        if l.startswith("*END"): cur=None; continue
        if sec=="r":
            p=l.split()
            if len(p)>=4: res[cur][1]+=float(p[-1]); res[cur][2]+=1
for k,v in res.items(): print(k,"Ctot %.2f fF  Rsum %.1f ohm  nres %d"%tuple(v))

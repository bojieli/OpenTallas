import sys, collections, re
for f in ("core.txt","hr.txt"):
    rows=[]
    for l in open(f):
        p=l.split()
        if len(p)<6 or p[3]=='-': continue
        rows.append((int(p[1]),float(p[2]),int(p[3])/1000,int(p[4])/1000,p[5]))
    b=[r for r in rows if r[0]==1]
    print("==",f,"boundary",len(b),"min",min(r[1] for r in b),"max",max(r[1] for r in b))
    # bucket by face/position
    def face(r):
        x,y=r[2],r[3]
        if y<60: return "S"
        if y>500: return "N"
        if x>715: return "E"
        return "IN"
    g=collections.defaultdict(list)
    for r in b: g[(face(r), int(r[2]//100)*100)].append(r[1])
    for k in sorted(g): v=g[k]; print(k,len(v),round(min(v)),round(max(v)),round(sum(v)/len(v)))
    # prefix groups
    pg=collections.defaultdict(list)
    for r in b:
        n=re.sub(r'\[\d+\]|\\\[\d+\\\]|_\d+_','',r[4]); n='/'.join(n.split('.')[:3])[:60]
        pg[n].append(r)
    print("-- by name (n,min,max, x-range,y-range)")
    for k,v in sorted(pg.items(), key=lambda kv:-len(kv[1]))[:25]:
        print(k,len(v),round(min(r[1] for r in v)),round(max(r[1] for r in v)),(round(min(r[2] for r in v)),round(max(r[2] for r in v))),(round(min(r[3] for r in v)),round(max(r[3] for r in v))))

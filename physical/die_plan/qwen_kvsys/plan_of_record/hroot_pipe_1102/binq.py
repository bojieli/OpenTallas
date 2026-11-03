import sys,re,json
sys.path.insert(0,'/tmp'); import dkv61h_geom_rules as G
D=G.Design(sys.argv[1]); rs=json.load(open(sys.argv[2]))
def key(n):
    n=n.replace('\\','');n=re.sub(r'\$_[A-Za-z0-9_]*$','',n)
    return re.sub(r'^[^./]*[./]','',n)
k2id={}
for i,c in D.cells.items():
    if c[0]=='S': k2id[key(c[6])]=i
def nb(start,rev):
    out=set();stack=[start];seen=set()
    while stack:
        cur=stack.pop()
        refs=[D.nets[n][1] for n,ck in D.cell_in.get(cur,[]) if not ck and D.nets[n][1]] if rev else [s for n in D.drives.get(cur,[]) for s in D.nets[n][2] if not s[2]]
        for kind,j,ck in refs:
            if ck or kind=='p': continue
            if D.kind(j) in 'SM': out.add(j)
            elif j not in seen: seen.add(j);stack.append(j)
    return out
d=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
moves={};worst=0;miss=0
for k,site in rs.items():
    if not re.match(r'u_bin_.*/q(\[\d+\])?$',k): continue
    i=k2id.get(k)
    if i is None: miss+=1; continue
    fr=[G.ctr(D.cells[j]) for j in nb(i,True)]; to=[G.ctr(D.cells[j]) for j in nb(i,False) if j!=i]
    pts=fr+to
    h=max(d(site,p) for p in pts) if pts else 0
    worst=max(worst,h)
    if h>360:
        best=None
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        for x in range(int(min(xs)),int(max(xs))+1,2):
            for y in range(int(min(ys)),int(max(ys))+1,2):
                m=max(d((x,y),p) for p in pts)
                if best is None or m<best[0]-1e-9 or (abs(m-best[0])<1e-9 and d((x,y),site)<d(best[1],site)): best=(m,(x,y))
        moves[k]=dict(old=site,new=[float(best[1][0]),float(best[1][1])],old_max=round(h,1),new_max=round(best[0],1),n_from=len(fr),n_to=len(to))
print(json.dumps(dict(missing=miss,worst_before=round(worst,1),n_moves=len(moves),moves=moves),indent=1))

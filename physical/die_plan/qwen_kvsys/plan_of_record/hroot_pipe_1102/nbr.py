import sys,re,json
sys.path.insert(0,'/tmp'); import dkv61h_geom_rules as G
D=G.Design(sys.argv[1]); pats=sys.argv[2:]
name2id={c[6]:i for i,c in D.cells.items()}
def seqset(start,rev):
    out={};pins=set();stack=[start];seen=set()
    while stack:
        cur=stack.pop()
        if rev:
            refs=[(D.nets[n][1],n) for n,ck in D.cell_in.get(cur,[]) if not ck and D.nets[n][1]]
        else:
            refs=[(s,n) for n in D.drives.get(cur,[]) for s in D.nets[n][2] if not s[2]]
        for (kind,j,ck),n in refs:
            if ck: continue
            if kind=='p': pins.add(D.pin_by_k[j]['name']+'@%.0f,%.0f'%(D.pin_by_k[j]['x'],D.pin_by_k[j]['y'])); continue
            if D.kind(j)=='S' or D.kind(j)=='M': out[j]=D.nets[n][0]
            elif j not in seen: seen.add(j); stack.append(j)
    return out,pins
for p in pats:
    rx=re.compile(p)
    for i,c in D.cells.items():
        if c[0]=='S' and rx.search(c[6]):
            x,y=G.ctr(c)
            print('==',c[6],'@%.1f,%.1f'%(x,y),c[1])
            for rev,lab in ((True,'FROM'),(False,'TO')):
                s,pins=seqset(i,rev)
                ds=sorted(((abs(G.ctr(D.cells[j])[0]-x)+abs(G.ctr(D.cells[j])[1]-y)),D.cells[j][6],G.ctr(D.cells[j])) for j in s)
                print('  ',lab,len(s),'pins',sorted(pins)[:6])
                for d in ds[-6:][::-1]: print('     %.0f %s @%.0f,%.0f'%(d[0],d[1],d[2][0],d[2][1]))

import json,collections,re
R=json.load(open('/tmp/trx/rows_o.json'))
def nn(n):
    i=n.find('[');b,s=(n[:i],n[i:]) if i>=0 else (n,'')
    return re.sub(r'(?<=_)\d+(?=_)','N',b)+s
def tab(r,o='R0',norm=True,names=True):
    w,h=r['w'],r['h'];out=[]
    for p in r['pins']:
        x,y=float(p['x']),float(p['y'])
        if o in('MY','R180'):x=w-x
        if o in('MX','R180'):y=h-y
        out.append(((nn(p['name']) if norm else p['name']) if names else '',p.get('layer'),round(x,2),round(y,2)))
    return tuple(sorted(out))
def face(r):
    w,h=r['w'],r['h'];f={}
    for p in r['pins']:
        x,y=float(p['x']),float(p['y']);dd={'W':x,'E':w-x,'S':y,'N':h-y};f[nn(p['name'])]=min(dd,key=dd.get)
    return tuple(sorted(f.items()))
G=collections.defaultdict(list)
for r in R: G[r['ms']].append(r)
print('master|nmod|ntype_inst|die_inst|outl|normnames|tabs_norm|tabs_norm_orient|geom_only(no names)|facemaps')
S=dict(a=0,b=0,c=0,d=0,e=0)
for ms,L in sorted(G.items(),key=lambda x:-len(x[1])):
    mods={r['mod'] for r in L}
    outl={(r['w'],r['h']) for r in L}
    nm={tuple(sorted(set(nn(p['name']) for p in r['pins']))) for r in L}
    t={tab(r) for r in L}
    to={min(tab(r,o) for o in('R0','MX','MY','R180')) for r in L}
    g={tab(r,names=False) for r in L}
    fm={face(r) for r in L}
    S['a']+=len(mods);S['b']+=len(t);S['c']+=len(to);S['d']+=len(nm);S['e']+=len(fm)
    if len(mods)>1 or len(t)>1:
        print(ms,'|',len(mods),'|',len(L),'|',sum(r['ni'] for r in L),'|',len(outl),'|',len(nm),'|',len(t),'|',len(to),'|',len(g),'|',len(fm))
print('masters',len(G),S)

import json,collections
R=json.load(open('/tmp/trx/rows.json'))
def tab(r,o='R0'):
    w,h=r['w'],r['h'];out=[]
    for p in r['pins']:
        x,y=float(p['x']),float(p['y'])
        if o in('MY','R180'):x=w-x
        if o in('MX','R180'):y=h-y
        out.append((p['name'],p.get('layer'),round(x,2),round(y,2)))
    return tuple(sorted(out))
def face(r):
    w,h=r['w'],r['h'];f={}
    for p in r['pins']:
        x,y=float(p['x']),float(p['y']);dd={'W':x,'E':w-x,'S':y,'N':h-y};f[p['name']]=min(dd,key=dd.get)
    return tuple(sorted(f.items()))
def facecnt(r):
    return tuple(sorted(collections.Counter(v for _,v in face(r)).items()))
G=collections.defaultdict(list)
for r in R: G[r['ms']].append(r)
tot=dict(mods=0,tabs=0,tabs_o=0,names=0)
mtabs=collections.Counter()
for r in R: mtabs[r['mod']]+=0
modtabs=collections.defaultdict(set)
for r in R: modtabs[r['mod']].add(tab(r))
print('pin tables total',sum(len(v) for v in modtabs.values()))
print('modules with >1 table:',{m:len(v) for m,v in modtabs.items() if len(v)>1})
print()
print('master | nmod | ninst(type) | dieinst | outlines | namesets | tabs | tabs mod-orient | facemaps | facecounts')
for ms,L in sorted(G.items(),key=lambda x:-len(x[1])):
    mods={r['mod'] for r in L}
    outl={(r['w'],r['h']) for r in L}
    names={tuple(sorted(p['name'] for p in r['pins'])) for r in L}
    tabs={tab(r) for r in L}
    tabso={min(tab(r,o) for o in ('R0','MX','MY','R180')) for r in L}
    fm={face(r) for r in L}; fc={facecnt(r) for r in L}
    if len(mods)>1 or len(tabs)>1:
        print(ms,'|',len(mods),'|',len(L),'|',sum(r['ni'] for r in L),'|',len(outl),'|',len(names),'|',len(tabs),'|',len(tabso),'|',len(fm),'|',len(fc), '| npins',sorted({len(r['pins']) for r in L}))

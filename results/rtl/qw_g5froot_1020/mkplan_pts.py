import json,re,sys,statistics,collections
case=sys.argv[1]; out=sys.argv[2]
fl=json.load(open(case+'/fwd_lanes.json'))
pl={}
for mm in re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)', open(case+'/place.tcl').read()): pl[mm[1]]=(float(mm[2]),float(mm[3]))
dv=open(case+'/die.v').read()
landm={n:mst for mst,n in re.findall(r'^\s*(qfd_landh\w*)\s+(\w+)\s*\(',dv,re.M)}
own=collections.defaultdict(list); miss=[]
for r in fl['lanes']:
    L=r.get('landing')
    if L in landm:
        if L not in pl: miss.append(L); continue
        own[r['dst']].append(pl[L])
print('landings',len(landm),'in lanes',sum(len(v) for v in own.values()),'owners',len(own),'miss',miss[:5])
nl=set(l for v in own.values() for l in v)
o={k:dict(xy=[round(statistics.median(p[0] for p in v),3),round(statistics.median(p[1] for p in v),3)],landings=len(v),pts=[[round(p[0],3),round(p[1],3)] for p in sorted(v)]) for k,v in sorted(own.items())}
lef=open(case+'/elements.lef').read()
sz={mm[1]:(float(mm[2]),float(mm[3])) for mm in re.finditer(r'MACRO (\S+)\n(?:.*\n){0,3}?\s*SIZE ([\d.]+) BY ([\d.]+)',lef)}
mst={n:ms for ms,n in re.findall(r'^\s*(qfd_\w+)\s+(rly_\w+)\s*\(',dv,re.M)}
res=[]
for n,ms in mst.items():
    if n in pl and ms in sz: x,y=pl[n]; w,h=sz[ms]; res.append([x,y,round(x+w,3),round(y+h,3)])
print('reserved',len(res),'of',len(mst))
json.dump(dict(reserved=res, schema='opentallas.qwen.fault-emit-plan.v1',source=case,owners=o,landings=len(landm)),open(out,'w'),indent=1)

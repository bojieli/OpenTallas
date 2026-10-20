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
o={k:dict(xy=[round(statistics.median(p[0] for p in v),3),round(statistics.median(p[1] for p in v),3)],landings=len(v)) for k,v in sorted(own.items())}
json.dump(dict(schema='opentallas.qwen.fault-emit-plan.v1',source=case,owners=o,landings=len(landm)),open(out,'w'),indent=1)

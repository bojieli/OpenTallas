import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-41/tools/die_plan')
import schema as S, lane_add as LA
raw=json.load(open(sys.argv[1])); P=S.Plan(raw)
rows=json.load(open(sys.argv[2]))['rows']
per=6.0; tm=0.6
def maxpins(lo,hi,layers):
    # largest pins with window_for(lo,pins)<=hi
    a,b=1,int((hi-lo)*per)+2
    while S.window_for(lo,b,layers,P.layers,per_um=per,track_max=tm)<=hi+1e-6: b*=2
    while a<b:
        m=(a+b+1)//2
        if S.window_for(lo,m,layers,P.layers,per_um=per,track_max=tm)<=hi+1e-6: a=m
        else: b=m-1
    return a
pairl={}
for lid,ln in P.lanes.items():
    hp=[P.ports[q] for q in ln['ports']]
    pairl.setdefault((hp[0]['src']['part'],hp[-1]['dst']['part']),[]).append(lid)
for r in rows:
    a,b,need=r['src'],r['dst'],r['unplanned_bits']
    out=[]
    for lid in pairl.get((a,b),[]):
        hp=[P.ports[q] for q in P.lanes[lid]['ports']]
        sp=[]; 
        for x in hp:
            segs=S.port_segments(x)
            if len(segs)>1 or 'window_um' not in x: sp.append(-1); continue
            lo,hi=sorted(x['window_um']); mp=maxpins(lo,hi,x['layers'])
            sp.append(mp-(x['width']+1))
        cyc=raw['latency']['lanes'].get(lid,{}).get('cycles')
        out.append(f"{lid}(w{hp[0]['width']},c{cyc},spare{min(sp)},{hp[0].get('kind')})")
    print(a,b,need,' '.join(out))

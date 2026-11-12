import json,sys,math,itertools
sys.path.insert(0,sys.argv[2]); sys.path.insert(0,'.')
import schema as S, pack as PK
raw=json.load(open(sys.argv[1]));P=S.Plan(raw);T=raw['partition_types'];pm={p['name']:p for p in raw['partitions']}
L=8.64; WB=4492.80; w0=457.92
TOP=['b001','b002','b003'];BOT=['b010','b011','b012','b013']
DEM={'NE':dict(b001_b011=570,b002_b011=310,b001_b010=830,b003_b013=760),
     'NW':dict(b001_b011=575,b002_b011=300,b001_b010=600,b003_b013=720)}
HB={'NE':2479.68,'NW':2531.52}
for side in ('NW',):
    bs={side+'_'+b for b in ['b000']+TOP+BOT}
    x0=P.rect(side+'_b000')[0] if side=='NE' else P.rect(side+'_b000')[2]
    sg=1 if side=='NE' else -1
    U=lambda x:(x-x0)*sg
    N=[];Sx=[]
    for pid,pr in P.ports.items():
        s,d=pr['src']['part'],pr['dst']['part']
        if (s in bs)==(d in bs): continue
        o=d if s in bs else s
        if o.endswith('hub') or o.endswith('_io'): continue
        for _,_,w in S.port_segments(pr):
            a,b=sorted((U(w[0]),U(w[1]))); r=P.rect(o)
            if r[3]<=6065.28+1: Sx.append((a,b))
            elif r[1]>=10385.28-1: N.append((a,b))
    ok=lambda s,ws: all(not(a-0.6<s<b+0.6) for a,b in ws)
    hb=HB[side]; ht=4320-hb
    area={b:P.ptype(side+'_'+b)['outline_um'][0]*4320 for b in TOP+BOT}
    cores={b:[dict(inst=c['inst'],w=c['outline_um'][0],h=c['outline_um'][1]) for c in T[pm[side+'_'+b]['type']]['hard_cores']] for b in TOP+BOT}
    minw={b:PK.min_width(ht if b in TOP else hb,cores[b]) for b in TOP+BOT}
    cand_top=[k*L for k in range(int(w0/L)+1,int(WB/L)) if ok(k*L,N)]
    cand_bot=[k*L for k in range(int(w0/L)+1,int(WB/L)) if ok(k*L,Sx)]
    D=DEM[side]; best=None
    need={b:area[b]/(ht if b in TOP else hb) for b in TOP+BOT}
    for s1 in cand_top:
        if s1-w0<minw['b001']: continue
        for s2 in cand_top:
            if s2-s1<minw['b002'] or WB-s2<minw['b003']: continue
            for t1 in cand_bot:
                if t1-w0<minw['b010'] or s1-t1<D['b001_b011'] or t1-w0<D['b001_b010']: continue
                for t2 in cand_bot:
                    if t2-t1<minw['b011'] or t2-s1<D['b002_b011']: continue
                    for t3 in cand_bot:
                        if t3-t2<minw['b012'] or WB-t3<minw['b013'] or WB-max(s2,t3)<D['b003_b013']: continue
                        e=dict(b001=s1-w0,b002=s2-s1,b003=WB-s2,b010=t1-w0,b011=t2-t1,b012=t3-t2,b013=WB-t3)
                        c=sum(((e[b]-need[b])/need[b])**2 for b in e)
                        if best is None or c<best[0]: best=(round(c,4),[round(s1,2),round(s2,2)],[round(t1,2),round(t2,2),round(t3,2)],{b:round((e[b]-need[b])/need[b],3) for b in e})
    print(side,'hb',hb,'best',best,'minw',minw)

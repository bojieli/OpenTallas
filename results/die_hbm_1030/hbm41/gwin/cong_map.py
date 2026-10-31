#!/usr/bin/env python3
"""Aggregate an OpenROAD GRT congestion report: overflow per 100-um tile and per lane (net-name lane token)."""
import re,sys,collections,json
def parse(p):
    out=[];cur={}
    for ln in open(p):
        if ln.startswith('violation type'): cur={'dir':ln.split(':')[1].strip()}
        elif 'srcs:' in ln: cur['nets']=ln.split('srcs:')[1].split()
        elif 'comment:' in ln:
            m=re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)',ln); cur['cap'],cur['use'],cur['ov']=map(int,m.groups())
        elif 'bbox' in ln:
            v=list(map(float,re.findall(r'-?\d+\.?\d*',ln)[:4])); cur['bb']=v; out.append(cur)
    return out
def lane(n):
    n=n.split(':',1)[1]
    m=re.match(r'(?:nq_st_|nd_bf_)?(L\w+?)(?:_[io])?(?:_\d+)*(?:\[\d+\])?$',n)
    return m.group(1) if m else n[:12]
if __name__=='__main__':
    T=float(sys.argv[2]) if len(sys.argv)>2 else 100
    v=parse(sys.argv[1]); tiles=collections.Counter(); lanes=collections.Counter(); dirs=collections.Counter()
    for c in v:
        x,y=(c['bb'][0]+c['bb'][2])/2,(c['bb'][1]+c['bb'][3])/2
        tiles[(int(x//T),int(y//T))]+=c['ov']; dirs[c['dir']]+=c['ov']
        ls=collections.Counter(lane(n) for n in c['nets'])
        tot=sum(ls.values())
        for l,k in ls.items(): lanes[l]+=c['ov']*k/tot
    print('violations',len(v),'sum_ov',sum(c['ov'] for c in v),dict(dirs))
    print('top tiles (x0,y0 um):',[((a*T,b*T),o) for (a,b),o in tiles.most_common(15)])
    print('top lanes:',[(l,round(o)) for l,o in lanes.most_common(12)])
    json.dump({'tiles':{f'{a},{b}':o for (a,b),o in tiles.items()},'lanes':lanes},open(sys.argv[1]+'.map.json','w'))

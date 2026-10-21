"""QDQ r3 price/strap composition used by the existing l12 bank-budget pass.

XR is the real maximum stage count on the request, read-return and write lanes.
Shorter internal paths are padded to XR, including each disjoint word slice.
RL prices the external VM path at the LG bank pins, independently of XR.
"""
import collections


def price(c,N,L,rep):
    q=c.get('qdq_split')
    if not q:return
    I=c['instances'];G=L.Graph(c);groups=collections.defaultdict(list);raw=[]
    lgs=set(q['lgs']);ctl=q['ctl'];children=set(c['split_parents'][q['parent']]['children'])
    # Every real internal sink bit is traced through the existing actual relay graph.
    for n in sorted(children):
        for p,pd in I[n]['ports'].items():
            if pd['direction']!='input':continue
            for b in range(pd['bits']):
                d,hops=G.back(n,p,b)
                if d is None:continue
                relevant=(n in lgs and p=='rq_i' and d[0]==ctl and d[1]=='rq')
                relevant|=(n in lgs and p=='wq_i' and d[0] in children and I[d[0]]['master']=='ot_hgi_qdq_transport_wslice')
                relevant|=(d[0] in lgs and d[1]=='rr_o' and
                    ((n==ctl and p=='rr_v') or I[n]['master']=='ot_hgi_qdq_transport_rslice'))
                if not relevant:continue
                lat,notes=G.lane_latency(hops)
                raw.append(dict(sink=[n,p,b],source=list(d),stages=lat,notes=notes))
                groups[(n,p,lat)].append(b)
    if not raw:raise ValueError('QDQ split internal relay paths missing')
    xr=max(x['stages'] for x in raw)
    if q['RL']+4+2*xr>126 or q['WC']+2+xr>63:
        rep['over_budget'].append(dict(client=q['parent'],RL=q['RL'],WC=q['WC'],XR=xr,reason='actual QDQ ctl_r4 range exceeded'))
        return
    for (n,p,lat),bits in sorted(groups.items()):
        if lat==xr:continue
        N.pad_snk('l12p_qdq_'+n+'_'+p+'_'+str(lat),n,p,bits,xr-lat,n,
            f'QDQ r3 fixed calendar: internal {p} path {lat} -> XR {xr}, read +3+XR/write +9+3XR')
    q['XR']=xr;q['RLI']=q['RL']+4+2*xr;q['WCI']=q['WC']+2+xr
    q['timing']=dict(rq=3+xr,wq=9+3*xr,beat_done=9+3*xr,record_done=9+3*xr)
    q['calendar_price']=dict(read_slot_offset=3+xr,write_slot_offset=9+3*xr,done_slot_offset=9+3*xr,
        base_RL=q['RL'],WC=q['WC'],XR=xr,source='ot_hgi_qdq_host_split_r3: RLI=RL+4+2*XR, WCI=WC+2+XR')
    found=set()
    for strap in c['straps']:
        if strap['inst']==ctl and strap['port'] in ('rl_cfg','wc_cfg'):
            strap['value']=q['RLI'] if strap['port']=='rl_cfg' else q['WCI'];found.add(strap['port'])
            strap['reason']='QDQ r3 actual l12-priced VM and equalized internal relay stages'
    if found!={'rl_cfg','wc_cfg'}:raise ValueError('QDQ controller real runtime straps missing')
    rep['qdq_split']=dict(RL=q['RL'],WC=q['WC'],XR=xr,RLI=q['RLI'],WCI=q['WCI'],
        physical_path_stage_counts=sorted(set(x['stages'] for x in raw)),
        internal_paths=len(raw),calendar_price=q['calendar_price'])
    N.commit()

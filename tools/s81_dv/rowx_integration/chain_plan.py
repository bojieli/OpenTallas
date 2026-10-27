#!/usr/bin/env python3
"""Compile the qualified ROWX3b chain's actual config words and endpoint calendar.

Input link cycles include codec TX/RX (one edge each) plus physical/PHY latency. No link/copy topology is invented.
The caller must provide a proved static circuit for both directions and a permutation of all sixteen owner IDs.
"""
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Link:
    wire_cycles: int
    jitter: int
    def hop(self):
        if any(type(x) is not int or x < 0 for x in (self.wire_cycles,self.jitter)):
            raise ValueError('link budgets must be measured nonnegative integer edges')
        return self.wire_cycles+self.jitter+2+4


def plan(links, owners, half, *, nsel=512, user=0, position=0, tag=0):
    if len(links)!=15 or sorted(owners)!=list(range(16)) or half not in (0,1):
        raise ValueError('require fifteen links and an exact sixteen-owner permutation, one real half')
    if not 0<nsel<=512 or not 0<=user<1024 or not 0<=position<1<<21 or not 0<=tag<256:
        raise ValueError('ROWX/SVC identity outside its real source field')
    ns=2240; nr=nsel; pk=1
    hops=[l.hop() for l in links]
    xoff=[2]
    for h in hops:xoff.append(xoff[-1]+h+pk)
    bc=[0]*16;bc[-1]=xoff[-1]+45
    for p in reversed(range(15)):bc[p]=bc[p+1]+hops[p]
    if max(xoff+bc)>=1<<16:raise ValueError('chain calendar does not fit XM 16-bit offsets')
    rows_header=6<<508|1<<503|tag<<495|(4*nsel)<<480|position<<459|user<<449|1
    cfg=[]
    for p,o in enumerate(owners):
        word=p|int(p==0)<<4|int(p==15)<<5|half<<6|xoff[p]<<7|bc[p]<<23|ns<<39|nr<<51|pk<<62
        cfg.append(dict(owner=o,pos=p,word=f'{word:016x}',xoff=xoff[p],bc_off=bc[p]))
    # Exactly fourteen existing 80-beat endpoint windows cover 1,120 packed beats.
    return dict(schema='opentallas.s81.rowx_chain.v1',half=half,owners=owners,config=cfg,
                rows_header=f'{rows_header:0128x}',export=dict(nxw=40,passes=7,period=320,words=ns),
                payload_words=4*nsel,packed_link_beats=1120,endpoint_windows=[dict(first=80*k,beats=80) for k in range(14)],
                codec_edges_per_link=2,codec_added_chain_edges=60,
                qualification='static XM calendar only; physical circuits, native drivers and integrated runtime still required')


if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('input');a.add_argument('output');v=a.parse_args()
    d=json.load(open(v.input));r=plan([Link(**l) for l in d['links']],d['owners'],d['half'],nsel=d.get('nsel',512),
                                    user=d.get('user',0),position=d.get('position',0),tag=d.get('tag',0))
    with open(v.output,'w') as f:json.dump(r,f,indent=2);f.write('\n')

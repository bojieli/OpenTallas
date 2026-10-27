#!/usr/bin/env python3
from chain_plan import Link,plan

def main():
    p=plan([Link(37,4)]*15,list(range(16)),1)
    assert len(p['config'])==16 and p['config'][0]['xoff']==2
    assert p['config'][-1]['xoff']==2+15*48
    assert p['config'][0]['bc_off']==2+15*48+45+15*47
    assert sum(w['beats'] for w in p['endpoint_windows'])==1120
    assert p['codec_added_chain_edges']==60
    for r in p['config']:
        w=int(r['word'],16)
        assert (w>>7)&0xffff==r['xoff'] and (w>>23)&0xffff==r['bc_off']
        assert (w>>39)&4095==2240 and (w>>51)&2047==512 and (w>>62)&1==1
    for owners in (list(range(15)),[0]*16):
        try:plan([Link(37,4)]*15,owners,0)
        except ValueError:pass
        else:raise AssertionError('owner mutant accepted')
    try:plan([Link(-1,4)]*15,list(range(16)),0)
    except ValueError:pass
    else:raise AssertionError('negative latency accepted')
    print('ROWX_CHAIN_PLAN PASS actual64b config, owner/latency controls, +60codec edges')
if __name__=='__main__':main()

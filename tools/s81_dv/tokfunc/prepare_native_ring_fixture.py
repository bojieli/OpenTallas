#!/usr/bin/env python3
"""Extend an experiment with native XQ/XB fragment inputs; no mission BF-operand claim."""
from pathlib import Path
import argparse,hashlib,json,sys

def main():
    p=argparse.ArgumentParser()
    for k in ('programme','fixture','source'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    sys.path[:0]=[str(a.source/'tools'),str(a.source/'tools/s81_dv'),str(a.source/'tools/s81_dv/layer_prog')]
    import numpy as np
    import hdc_golden_v41 as G
    import xs_calendar as X
    meta=json.loads((a.fixture/'files.json').read_text())['ops/attn.norm.scale.bin']
    input_path=a.fixture/'ops/attn.norm.scale.bin'
    x=np.fromfile(input_path,dtype=np.dtype(meta['dtype'])).reshape(-1)
    assert len(x)==5120
    xb=(G.to_bf16(x[:4096]).view(np.uint32)>>16).astype(np.uint16)
    report=json.loads((a.programme/'programme.json').read_text())
    for label in ['old','advance1']:
        d=a.programme/label;events=[];beats=[]
        for line in (d/'producer.txt').read_text().splitlines():
            t,k,v=line.split();t,k,v=int(t),int(k),int(v,16)
            if k==0:events.append((t,0,v))
            else:
                assert k==1
                index=v>>1024;data=v&((1<<1024)-1)
                beats.append((456+4*index,1,index,data))
        assert len(beats)==80
        # Native GW control selects the BF write parity; family itself is decoded by rstop from K_XB.
        body=X.isd(gw=1,gw_fam=1,gw_par=0)
        flit=1|(4<<9)|((1|(2<<16)|(body<<26))<<21)
        events.append((800,0,flit))
        report['programmes'][label]['expected_issuer_pin']['803']=f'{body:040x}'
        report['programmes'][label]['source_commands']['800']=f'{body:x}'
        for index in range(64):
            data=sum(int(v)<<(16*j)for j,v in enumerate(xb[64*index:64*(index+1)]))
            beats.append((900+4*index,2,index,data))
        for t,kind,index,data in beats:
            # Native header: valid[0], kind[3:1], hops[8:4], src[12:9], index[19:13].
            beat=1|(kind<<1)|(1<<4)|(index<<13)|(data<<21)
            for fragment in range(4):
                payload=((beat>>(276*fragment))&((1<<276)-1))|((fragment==0)<<276)
                events.append((t+fragment,2,payload))
        assert len(events)<1024 and len({(t,k)for t,k,v in events})==len(events)
        (d/'producer_DIRECT_GATHER_ORIGINAL.txt').write_bytes((d/'producer.txt').read_bytes())
        (d/'producer.txt').write_text(''.join(f'{t} {k} {v:x}\n'for t,k,v in sorted(events)))
    report['native_ring_fixture']=dict(actual_producer='ot_s81sl_rstop own xf_v[2] four-fragment assembly',
        authoritative_family='native header kind K_XQ=1/K_XB=2, decoded by production rstop',
        Q_beats=80,BF_beats=64,Q_start=456,BF_start=900,BF_window_source_date=800,
        BF_payload='checkpoint norm-scale prefix4096, golden BF16 conversion; component fixture only',
        checkpoint_input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
        phase106_mission_operand_qualified=False,production_enabled=False)
    (a.programme/'programme.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Selected rowpack pair image + legal W17/W10 PP configuration per subphase.
Raw format: address-major, two272-bit banks, little-endian34bytes/bank.
"""
import argparse,gzip,json
from pathlib import Path
import numpy as np
import dsrom_mtp_p2 as P
import v41_rom_ksplit_bankmap as S


def emit(plan,snapshot,side,rank,pair,out):
    assert 0<=rank<4 and 0<=pair<1792
    bank=np.zeros((8192,2,34),dtype=np.uint8);used=np.zeros(8192,dtype=bool)
    raw=P.Raw(snapshot);configs=[];blocks=0
    for ph in plan['phases']:
        if ph['side']!=side:continue
        ss=sorted([x for x in ph['segments'] if x['pair']==pair],key=lambda x:(x['superrow'],x['mi']))
        if not ss:continue
        segs=[dict(fmt='fp4',e0=0,elems=x['K'],row=x['superrow'],tensor=x['mi']) for x in ss]
        order=S.element_order(segs);base=min(x['base'] for x in ss)
        assert len(order)==sum(x['words'] for x in ss)
        assert not used[base:base+len(order)].any()
        cfg=[0]*25;k=ss[0]['K'];nu=(k+511)//512
        cfg[8]=1|(nu<<9)|((len(ss)-1)<<19)
        cfg[16]=( (nu+7)//8-1 )|(base<<6)
        arrays=[(raw.array(x['tensor']),raw.array(x['tensor'][:-6]+'scale')) for x in ss]
        for i,x in enumerate(ss):
            tag=2*x['superrow']+(576 if x['op']=='w3' else 0)
            cfg[i]=tag|(1<<21)|(1<<26)|(1<<27)|(int(k%512==0)<<28)|(x['base']<<29)
            cfg[17+i]=tag+1
        for j,(idx,u,b,h) in enumerate(order):
            x=ss[idx];codes,scale=arrays[idx]
            r0=x['rank_slices'][rank]['rows'][0]
            for mb in range(2):
                row=r0+2*x['superrow']+mb
                for half in range(2):
                    block=(2*u+half)*8+b
                    if block*32>=x['K']:continue
                    off=half*17
                    bank[base+j,mb,off:off+16]=codes[row,block*16:(block+1)*16]
                    bank[base+j,mb,off+16]=scale[row,block];blocks+=1
        used[base:base+len(order)]=True
        configs.append(dict(stage=ph['stage'],expert=ph['expert'],ops=ph['ops'],subphase=ph['subphase'],
                            cfg=cfg,PP_phase_base=base,read_words=len(order)))
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError(out)
    out.write_bytes(bank.tobytes())
    return dict(side=side,rank=rank,pair=pair,image_sha256=P.digest(out),source_sha256=P.digest(__file__),
                storage_words=int(used.sum()),released_blocks=blocks,configs=configs,
                qualified_field_schedule=False,production_qelement_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--snapshot',type=Path,default=P.D.SNAP_DEFAULT)
    p.add_argument('--side',choices=['A','B'],default='A');p.add_argument('--rank',type=int,default=0)
    p.add_argument('--pair',type=int,default=0);p.add_argument('--image',type=Path,required=True)
    p.add_argument('--record',type=Path,required=True);a=p.parse_args()
    b=a.plan.read_bytes();r=json.loads(gzip.decompress(b) if a.plan.suffix=='.gz' else b)
    proof=emit(r,a.snapshot,a.side,a.rank,a.pair,a.image)
    if a.record.exists():raise FileExistsError(a.record)
    a.record.write_text(json.dumps(proof,indent=1)+'\n');print(proof['storage_words'],proof['released_blocks'])
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Opt4 A-layout: source bytes, eight-sector bank-class chunks, no arithmetic.

Successor of the matrix-per-SM calibration, which remains immutable. Each
stack q supplies six w1/w3 row pairs to SM 4*slot+q. The caller supplies
actual ascending router IDs; no selector, checkpoint inference or warm-up is
fabricated. Returned schedules are a reference, never measured latency.
"""
from dataclasses import dataclass
import numpy as np
from dshbm_expert_workgroup import steer, weight_lines, exported_weight_reader
from rtl_gpu_sm_exact import issue_order

@dataclass(frozen=True)
class Chunk:
    slot: int
    expert: int
    bank_set: int
    row: int
    j0: int
    sectors: int
    keep: bool


def chunks(ids):
    steer(ids,0)  # authoritative released domain, uniqueness and router order
    ids=tuple(int(e) for e in ids)
    progress=[0]*6; visited=set(); out=[]
    while len(out)<24:
        fronts=[k for k in range(6) if progress[k]<4 and
                not any(ids[r]%7==ids[k]%7 and progress[r]<4 for r in range(k))]
        first=[k for k in fronts if ids[k]%7 not in visited]
        k=min(first) if first else min(fronts,key=lambda k:
            (-sum(4-progress[r] for r in range(6) if ids[r]%7==ids[k]%7),k))
        g=progress[k];out.append(Chunk(k,ids[k],ids[k]%7,ids[k]//7,g*8,8,g!=3))
        progress[k]+=1;visited.add(ids[k]%7)
    out += [Chunk(k,e,e%7,e//7,32,17,False) for k,e in enumerate(ids)]
    return tuple(out)


def paired_rows(reader, expert, die, stack):
    if not 0<=die<96 or not 0<=stack<4: raise ValueError('actual die/stack range')
    start=die*24+stack*6
    a,sa=reader(expert,'w1',start,start+6);b,sb=reader(expert,'w3',start,start+6)
    packed=np.empty((12,2560),np.uint8);scale=np.empty((12,160),np.uint8)
    packed[::2]=a;packed[1::2]=b;scale[::2]=sa;scale[1::2]=sb
    return packed,scale


def compact_stream(packed,scale):
    """255 source 128B lines + one explicit pad; original issue_order.

    Tail group has 64B codes then four UE8M0 scale bytes. No padding bytes are
    stored in HBM; the static gearbox restores the zero inactive-lane fields.
    """
    raw=bytearray()
    for word,(_,g,_) in zip(weight_lines(packed,scale),issue_order(12,3,8,True)):
        if g<2: raw += word.to_bytes(136,'little')
        else: raw += (word&((1<<512)-1)).to_bytes(64,'little') + (word>>1024).to_bytes(4,'little')
    assert len(raw)==32640
    return bytes(raw)+bytes(128)


def expand_stream(raw):
    if len(raw)!=32768 or any(raw[32640:]): raise ValueError('GU extent/pad')
    off=0;out=[]
    for _,g,_ in issue_order(12,3,8,True):
        n=136 if g<2 else 68;b=raw[off:off+n];off+=n
        out.append(int.from_bytes(b,'little') if g<2 else
                   int.from_bytes(b[:64],'little') | (int.from_bytes(b[64:],'little')<<1024))
    assert off==32640
    return tuple(out)


def sector_addresses(c,pc):
    if not 0<=pc<32: raise ValueError('PC range')
    return tuple((c.bank_set*4+((j&3)^((c.expert&1)<<1)),c.row,j>>2,
                  ((j*32+pc)>>2),(j*32+pc)&3) for j in range(c.j0,c.j0+c.sectors))

if __name__=='__main__':
    import argparse,json,pathlib
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--weight-rows',required=True);p.add_argument('--ids-u32',required=True)
    p.add_argument('--layer',type=int,choices=(3,20),required=True)
    p.add_argument('--die',type=int,default=0);p.add_argument('--stack',type=int,default=0)
    p.add_argument('--out',required=True)
    a=p.parse_args();ids=tuple(map(int,np.fromfile(a.ids_u32,dtype='<u4')))
    plan=chunks(ids);reader=exported_weight_reader(a.weight_rows,a.layer,ids)
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    lines=[];sm_lines=[]
    for k,e in enumerate(ids):
        b,s=paired_rows(reader,e,a.die,a.stack);raw=compact_stream(b,s)
        lines += [int.from_bytes(raw[i:i+128],'little') for i in range(0,len(raw),128)]
        sm_lines += list(expand_stream(raw))
    (out/'gu.hex').write_text('\n'.join(f'{x:0256x}' for x in lines)+'\n')
    (out/'sm_expected.hex').write_text('\n'.join(f'{x:0272x}' for x in sm_lines)+'\n')
    (out/'ids.hex').write_text('\n'.join(f'{e:03x}' for e in ids)+'\n')
    (out/'plan.json').write_text(json.dumps(dict(layer=a.layer,die=a.die,stack=a.stack,
        ids=ids,sm_ids=[4*k+a.stack for k in range(6)],
        descriptors=[c.__dict__ for c in plan],start_delay_ps=None,measured=False),indent=2)+'\n')

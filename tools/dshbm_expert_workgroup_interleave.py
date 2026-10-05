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
    out=[]
    for base,count in ((0,4),(32,3)):
        progress=[0]*6; visited=set()
        while any(v<count for v in progress):
            fronts=[k for k in range(6) if progress[k]<count and
                    not any(ids[r]%7==ids[k]%7 and progress[r]<count for r in range(k))]
            first=[k for k in fronts if ids[k]%7 not in visited]
            k=min(first) if first else min(fronts,key=lambda k:
                (-sum(count-progress[r] for r in range(6) if ids[r]%7==ids[k]%7),k))
            g=progress[k]; j0=base+g*8
            out.append(Chunk(k,ids[k],ids[k]%7,ids[k]//7,j0,1 if j0==48 else 8,g!=count-1))
            progress[k]+=1;visited.add(ids[k]%7)
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


def w2_source_rows(reader, expert, die, stack):
    """Retain W19's greedy 32-SM row assignment, using actual TP96 row bounds.

    W19 allocates capacity for 54 rows. A 53-row die's last capacity row is
    padding, never a fabricated released tensor row. This returns each SM's
    actual raw fields and its legacy GU/W2 line seam, not uniform 17-line data.
    """
    if not 0<=die<96 or not 0<=stack<4:
        raise ValueError('actual die/stack range')
    start,stop=die*5120//96,(die+1)*5120//96
    sizes=[0]*32;gu=[0]*32;owners=[[] for _ in range(32)]
    for _ in range(48):
        m=min(range(32),key=lambda m:(sizes[m],m))
        sizes[m]+=2720;gu[m]+=2720
    for row in range(54):
        m=min(range(32),key=lambda m:(sizes[m],m));sizes[m]+=1224
        if start+row<stop: owners[m].append(start+row)
    out=[]
    for m in range(stack,32,4):
        rows=owners[m]
        p=np.empty((len(rows),1152),np.uint8);s=np.empty((len(rows),72),np.uint8)
        for k,r in enumerate(rows):
            a,b=reader(expert,'w2',r,r+1)
            if a.dtype!=np.uint8 or a.shape!=(1,1152) or b.dtype!=np.uint8 or b.shape!=(1,72):
                raise ValueError('released W2 raw FP4/UE8M0 shape')
            p[k]=a[0];s[k]=b[0]
        capacity=(sizes[m]+127)//128-(gu[m]+127)//128
        out.append(dict(sm=m,rows=tuple(rows),packed=p,scale=s,
            prefix_bytes=min((-gu[m])%128,len(rows)*1224),suffix_capacity_lines=capacity))
    return tuple(out)


def w2_compact_stream(packed,scale):
    """Existing native FP4 issue_order: 72 blocks, C8/G2, no re-encoding.

    The last group carries ONE active lane (17 bytes), not GU's four lanes.
    Retains all 1224 bytes per row; the legacy cfg tail alone omits 64/96 bytes.
    """
    if packed.dtype!=np.uint8 or packed.ndim!=2 or packed.shape[1]!=1152 or scale.dtype!=np.uint8 or scale.shape!=(len(packed),72):
        raise ValueError('W2 raw field shape/type')
    raw=bytearray();words=[]
    for r,g,t in issue_order(len(packed),2,8,True):
        word=0
        for lane in range(8):
            block=(g*8+lane)*8+t
            if block<72:
                word|=int.from_bytes(packed[r,block*16:(block+1)*16].tobytes(),'little')<<(128*lane)
                word|=int(scale[r,block])<<(1024+8*lane)
        words.append(word)
        raw+=word.to_bytes(136,'little') if g==0 else (word&((1<<128)-1)).to_bytes(16,'little')+(word>>1024).to_bytes(1,'little')
    assert len(raw)==len(packed)*1224
    return bytes(raw),tuple(words)


def w2_legacy_tail(views):
    """Exact cfg_lut suffix ownership + four zero transport pads for stack0.

    Prefix bytes belong to the final legacy GU line and are returned separately:
    callers MUST assemble them before W2 numerical execution. This helper does
    not qualify the current GU pad-only gearbox for delivering these prefixes.
    """
    lut=[];tail=bytearray();prefixes={};native={}
    for local,v in enumerate(views):
        raw,words=w2_compact_stream(v['packed'],v['scale']);n=v['prefix_bytes']
        prefixes[local]=raw[:n];native[local]=words
        suffix=raw[n:];capacity=v['suffix_capacity_lines']*128
        if len(suffix)>capacity: raise ValueError('legacy W2 tail capacity')
        tail+=suffix+bytes(capacity-len(suffix))
        lut.extend((local,line) for line in range(v['suffix_capacity_lines']))
    if len(lut)>136: raise ValueError('W2 stack sector extent')
    pad=136-len(lut);tail+=bytes(pad*128);lut.extend((255,255) for _ in range(pad))
    return bytes(tail),tuple(lut),prefixes,native


def w2_exported_reader(root,layer,ids):
    """Read only the enrolled released die2 source slices (no input inference)."""
    from pathlib import Path
    import json,hashlib
    root=Path(root);rec=json.loads((root/'source.json').read_text())
    if rec['layer']!=layer or tuple(rec['expert_ids'])!=tuple(ids):
        raise ValueError('W2 released slice owner')
    fields={}
    for t in rec['tensors']:
        p=root/t['file'];raw=p.read_bytes()
        if len(raw)!=t['bytes'] or hashlib.sha256(raw).hexdigest()!=t['sha256']:
            raise ValueError('W2 released bytes changed')
        parts=t['tensor'].split('.');expert=int(parts[4]);kind='packed' if parts[-1]=='weight' else 'scale'
        fields[expert,kind]=(np.frombuffer(raw,np.uint8).reshape(t['shape']),t['row_start'],t['row_stop'])
    def read(e,m,start,stop):
        if m!='w2':raise ValueError('W2 only')
        result=[]
        for kind in ('packed','scale'):
            data,a,b=fields[e,kind]
            if not a<=start<=stop<=b:raise ValueError('released slice row bounds')
            result.append(data[start-a:stop-a].copy())
        return tuple(result)
    return read


def w2_stream(views):
    """Standalone complete W2 rows in the unchanged 136-line sector extent.

    GU's new compact A-layout no longer carries legacy 64/96-byte seams.
    Repack those SAME W2 bytes into their own SM's final tail line. Counts
    change 10,10,0,0,28,28,28,28 -> 10,10,0,0,29,29,29,29, with no new sectors,
    no separate prefix store or payload loss, and no change to FP4 issue order.
    The caller must use this returned literal cfg_lut/counts together.
    """
    tail=bytearray();lut=[];counts=[];native={}
    for local,v in enumerate(views):
        raw,words=w2_compact_stream(v['packed'],v['scale'])
        n=(len(raw)+127)//128;counts.append(n);native[local]=words
        tail+=raw+bytes(n*128-len(raw));lut.extend((local,line) for line in range(n))
    if len(lut)>136:raise ValueError('W2 source-owned sector capacity')
    pad=136-len(lut);tail+=bytes(pad*128);lut.extend((255,255) for _ in range(pad))
    return bytes(tail),tuple(lut),tuple(counts),native

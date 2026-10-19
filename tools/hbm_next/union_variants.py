#!/usr/bin/env python3
"""Compile preinstalled U-only HGI-1R suffix banks. No runtime code generation.

Each layer executes its common prefix through IDX.UNION, then a hardware selector chooses
one immutable suffix by U. Both expert loops have immediate counts, never VM-loop counts.
The suffix preserves VM addresses, row-table references and per-position kappa order.
This record bank is not a native static calendar: binding record references to timed
unit launch descriptors remains the HGI-1R dispatcher integration boundary.
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hbm_next import image_check as IC, isa_rows as IR

def compile_banks(image, meta, out, capacity=64<<20):
    out.mkdir(parents=True, exist_ok=True)
    rows=IC.decode_all(image)
    groups={}
    table=meta['token']['segments']
    for row in rows:
        key=IC.seg_of(table,row[0])
        groups.setdefault(str(key),[]).append(row)
    bank=bytearray(); manifest=[]
    for layer, rr in groups.items():
        ui=[i for i,x in enumerate(rr) if x[1].unit=='IDX' and x[1].op=='UNION']
        if not ui: continue
        assert len(ui)==1, 'one route boundary per layer'
        i=ui[0]; route=rr[i][1]; N=route.desc['A'].m; k=route.desc['A'].n
        suffix=rr[i+1:]; variants=[]
        for u in range(k,k*N+1):
            b=bytearray(); loops=0
            for _,r,rx,_ in suffix:
                r=copy.deepcopy(r)
                if r.unit=='CTL' and r.op=='LOOP':
                    assert r.param & (1<<17)
                    r.param=(r.param & ~((1<<17)|65535)) | u
                    r.imm_a=0; loops+=1
                b.extend(IR.encode(r,rx))
            assert loops==2, (layer,loops)
            # Verify independently after encode: both loops have the selected immediate count.
            ds=IC.decode_all(bytes(b))
            assert all(not(r.param&(1<<17)) and (r.param&65535)==u
                       for _,r,_,_ in ds if r.unit=='CTL' and r.op=='LOOP')
            variants.append(bytes(b))
        stride=1<<(max(map(len,variants))-1).bit_length()
        base=(len(bank)+stride-1)//stride*stride
        bank.extend(bytes(base-len(bank)))
        for u,b in zip(range(k,k*N+1),variants):
            bank.extend(b); bank.extend(bytes(stride-len(b)))
        manifest.append(dict(layer=layer,N=N,topk=k,U_min=k,U_max=k*N,base_bytes=base,
            stride_bytes=stride,stride_log2=stride.bit_length()-1,variant_bytes=len(variants[0]),
            variants=len(variants),route_end=rr[i][0]+len(rr[i][3]),
            loop_body_max_bytes=max(_loop_sizes(variants[0])),
            safety='reserve N rows for each expert; U does not determine cardinality profile'))
    assert len(bank)<=capacity, f'bank capacity {len(bank)} > {capacity}'
    assert max(m['loop_body_max_bytes'] for m in manifest)<65536, '64 KiB CP ring loop-body fit'
    (out/'banks.hgi1r').write_bytes(bank)
    result=dict(schema='hnx.union_variants.v1',source_sha256=hashlib.sha256(image).hexdigest(),
        capacity_bytes=capacity,bank_bytes=len(bank),bank_sha256=hashlib.sha256(bank).hexdigest(),
        layers=manifest,selector='base_bytes + ((U-topk) << stride_log2)',
        native_die_bound=False,calendar_bound=False,
        integration_gap='HGI-1R descriptor/calendar dispatcher; legacy credit CP cannot execute static banks')
    (out/'manifest.json').write_text(json.dumps(result,indent=1)+'\n')
    return result

def _loop_sizes(blob):
    start=None; sizes=[]
    for off,r,rx,raw in IC.decode_all(blob):
        if r.unit=='CTL' and r.op=='LOOP': start=off+len(raw)
        if r.unit=='CTL' and r.op=='ENDLOOP':
            assert start is not None; sizes.append(off-start); start=None
    return sizes

def counterexample():
    # Two 6x6 strictly ascending route lists with U=24 and different maximum multiplicities.
    balanced=[list(range(6*i,6*i+6)) for i in range(4)]+[list(range(0,6)),list(range(6,12))]
    skew=[[0]+list(range(1+5*i,6+5*i)) for i in range(4)]+[[0,1,2,3,4,21],[0,5,6,7,22,23]]
    def profile(rows):
        from collections import Counter
        c=Counter(x for row in rows for x in row)
        assert all(len(row)==6 and row==sorted(set(row)) for row in rows)
        return dict(U=len(c),max_rows=max(c.values()),max_passes=(max(c.values())+2)//3,
            total_rows=sum(c.values()))
    a,b=profile(balanced),profile(skew)
    assert a['U']==b['U']==24 and a['max_passes']==1 and b['max_passes']==2
    return dict(balanced=a,skew=b,rows=dict(balanced=balanced,skew=skew),
        verdict='U-only mean/histogram timing is unsafe; reserve N rows per expert')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image',type=Path,required=True); ap.add_argument('--meta',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    r=compile_banks(a.image.read_bytes(),json.loads(a.meta.read_text()),a.out)
    (a.out/'counterexample.json').write_text(json.dumps(counterexample(),indent=1)+'\n')
    print(json.dumps(dict(PASS=True,bank_bytes=r['bank_bytes'],layers=len(r['layers']),
        capacity_bytes=r['capacity_bytes'],native_die_bound=False)))

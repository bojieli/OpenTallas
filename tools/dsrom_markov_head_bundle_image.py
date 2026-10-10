#!/usr/bin/env python3
"""Opt-in released bundle binding from the selected semantic vocabulary manifest.
A K0:4096, B K4096:5120 (n=4*k+q), Markov K256; default native images untouched.
Run image generation on an admitted remote host. No arithmetic or payload conversion.
"""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from dsrom_markov_head_weight_image import generate,DEFAULT,REV

KEY='head.weight'
def viamap(path,words):
    spread=[sum(((b>>k)&1)<<(8*k) for k in range(8)) for b in range(256)]
    p=[0]*512
    for a,row in enumerate(words):
        word=int.from_bytes(row.tobytes(),'little')
        expanded=sum(spread[(word>>(8*j))&255]<<(64*j) for j in range(32))
        p[a//8]|=expanded<<(a%8)
    path.write_text(''.join(f'{v:0548x}\n' for v in p))
    stored=[int(v,16) for v in path.read_text().splitlines()]
    for a,row in enumerate(words):
        got=sum(((stored[a//8]>>(8*bit+a%8))&1)<<bit for bit in range(256))
        if got!=int.from_bytes(row.tobytes(),'little'):raise ValueError('serialized macro payload mismatch')
def build(snapshot,manifest,out,die,bundle,sk=11,windows=None):
    m=json.loads(manifest.read_text())
    if m['released_vocab']!=129280 or m['head_dies']!=12:raise ValueError('unpriced manifest shape')
    d=next(x for x in m['dies'] if x['die']==die)
    b=next(x for x in d['bundles'] if x['bundle']==bundle)
    aa=b['A'];r0=b['global_row0'];nv=b['B_VALID_ROWS']
    if len(aa)!=4 or nv<0 or nv>128:raise ValueError('bundle shape')
    for q,a in enumerate(aa):
        want=max(0,min(32,nv-32*q))
        if a['global_row0']!=r0+32*q or a['VALID_ROWS']!=want:raise ValueError('A/B semantic row disagreement')
    out.mkdir(parents=True,exist_ok=False)
    rows=np.zeros((128,5120),dtype='<u2');markov_rows=None
    if windows is not None:
        provenance=json.loads((windows/'transfer_provenance.json').read_text())
        window=next(x for x in provenance['windows'] if x['die']==die and x['bundle']==bundle)
        if window['row0']!=r0 or window['VALID_ROWS']!=nv:raise ValueError('window row identity')
        wdir=windows/f'd{die}_b{bundle}'
        data=(wdir/'head.bin').read_bytes();raw_markov=(wdir/'markov.bin').read_bytes()
        if len(data)!=nv*10240 or len(raw_markov)!=nv*512:raise ValueError('window byte count')
        markov_rows=np.zeros((128,256),dtype='<u2')
        if nv:markov_rows[:nv]=np.frombuffer(raw_markov,dtype='<u2').reshape(nv,256)
        h=window['payloads'][0]['header'];index_sha=None
    else:
        ip=snapshot/'model.safetensors.index.json';idx=json.loads(ip.read_text())['weight_map'];shard=snapshot/idx[KEY]
        index_sha=hashlib.sha256(ip.read_bytes()).hexdigest()
        with shard.open('rb') as f:
            n=struct.unpack('<Q',f.read(8))[0];h=json.loads(f.read(n))[KEY]
            f.seek(8+n+h['data_offsets'][0]+r0*10240);data=f.read(nv*10240)
        if len(data)!=nv*10240:raise ValueError('truncated tensor')
    if h['shape']!=[129280,5120] or h['dtype']!='BF16':raise ValueError('released head shape/dtype')
    if nv and (r0<0 or r0+nv>129280):raise ValueError('released row bounds')
    if nv:rows[:nv]=np.frombuffer(data,dtype='<u2').reshape(nv,5120)
    p=np.arange(8192)[:,None];j=np.arange(16)[None,:]
    def image(logical,name):
        phys=logical[(p-sk*(j%8))%8192,np.broadcast_to(j,(8192,16))]
        # Invert the lane skew and compare every copied/padded BF16 word.
        inverse=phys[(p+sk*(j%8))%8192,np.broadcast_to(j,(8192,16))]
        if not np.array_equal(inverse,logical):raise ValueError('skew inverse mismatch')
        for half in (0,1):viamap(out/f'{name}_{half}.viamap.hex',phys[half::2])
        return dict(payload_sha256=hashlib.sha256(logical.tobytes()).hexdigest(),released_and_padding_readback=True)
    bindings=[]
    for q,a in enumerate(aa):
        rec=image(rows[32*q:32*q+32,:4096].reshape(8192,16),f'ha{q}')
        if markov_rows is None:
            mk=generate(snapshot,out/f'markov_A{q}',a['global_row0'],a['VALID_ROWS'],f'mk{q}')
            for half in (0,1):(out/f'mk{q}_{half}.viamap.hex').symlink_to(f'markov_A{q}/mk{q}_{half}.viamap.hex')
        else:
            mw=markov_rows[32*q:32*q+32].reshape(512,16)
            for half in (0,1):viamap(out/f'mk{q}_{half}.viamap.hex',mw[half::2])
            mk=dict(row0=a['global_row0'],VALID_ROWS=a['VALID_ROWS'],payload_sha256=hashlib.sha256(mw.tobytes()).hexdigest(),serialized_readback=True)
        bindings.append(dict(A=q,row0=a['global_row0'],VALID_ROWS=a['VALID_ROWS'],head=rec,Markov=mk))
    perm=np.array([32*q+k for k in range(32) for q in range(4)])
    brec=image(rows[perm,4096:].reshape(8192,16),'hb')
    rec=dict(schema='opentallas.md6.semantic-bundle-image.v1',adopted=False,checkpoint_revision=REV,key=KEY,checkpoint_header=h,index_sha256=index_sha,source_window_provenance=window if windows is not None else None,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),die=die,bundle=bundle,global_row0=r0,B_VALID_ROWS=nv,A=bindings,B=brec,K_spans=dict(A=[0,4096],B=[4096,5120],Markov=[0,256]),SK=sk,B_row_order='n=4*k+q; global row=global_row0+32*q+k',released_payload_sha256=hashlib.sha256(data).hexdigest(),padding_rows=128-nv,padding='zero image words; VALID_ROWS masks argmax; scheduled rows still consumed',ROM_ECC=False,images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.viamap.hex')})
    (out/'manifest.json').write_text(json.dumps(rec,indent=2)+'\n');return rec
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--snapshot',type=Path,default=DEFAULT);ap.add_argument('--windows',type=Path);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--die',type=int,required=True);ap.add_argument('--bundle',type=int,required=True);a=ap.parse_args();build(a.snapshot,a.manifest,a.out,a.die,a.bundle,windows=a.windows)

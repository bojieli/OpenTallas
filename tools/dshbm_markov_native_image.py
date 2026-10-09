#!/usr/bin/env python3
"""Compile released Markov rows into the actual native NC8 matrix record.

This emits a matvec component image. Runtime stored-logit addition and global
argmax are mandatory separate consumers; it does not emit a winning token.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

REVISION='dba1be0a40aa45a94ad051997016db3960a90277'
INDEX_SHA='74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8'
SHARD_SHA='e625902027b9d23d416f8818c665fab4704e0b96dc1bc778321601b700475a9d'

def sha(raw):return hashlib.sha256(raw).hexdigest()

def read_rows(snapshot,index,name,start,rows):
    path=snapshot/index[name]
    with path.open('rb') as f:
        n=struct.unpack('<Q',f.read(8))[0];header=f.read(n);meta=json.loads(header)[name]
        if meta['dtype']!='BF16' or len(meta['shape'])!=2:
            raise ValueError('released BF16 matrix required')
        r,k=meta['shape']
        if not 0<=start<r or not 0<rows<=r-start:raise ValueError('tensor row bounds')
        first=8+n+meta['data_offsets'][0]+start*k*2
        f.seek(first);raw=f.read(rows*k*2)
        if len(raw)!=rows*k*2:raise ValueError('truncated released tensor')
    receipt=dict(shard=str(path),tensor=name,dtype='BF16',shape=[r,k],
        rows=[start,start+rows],file_byte_offset=first,slice_sha256=sha(raw),header_sha256=sha(header))
    return raw,k,receipt

def generate(snapshot,out,token=21946,die=0,sm=0,dlog_fixture=None):
    snapshot,out=Path(snapshot),Path(out)
    index_path=snapshot/'model.safetensors.index.json'
    index_raw=index_path.read_bytes();index=json.loads(index_raw)['weight_map']
    if sha(index_raw)!=INDEX_SHA:raise ValueError('released pinned index mismatch')
    h=next(n for n in index if n.endswith('markov_head.head.weight'))
    e=next(n for n in index if n.endswith('markov_head.embed.weight'))
    # Exact contiguous TP96, then32SM row partition used by retained fullshape receipt.
    if die!=0 or sm!=0:raise ValueError('minimum busiest-SM source fixture only; full partition enrollment unresolved')
    if index[h]!=index[e] or index[h]!='model-00046-of-00048.safetensors':
        raise ValueError('released Markov tensor source changed')
    checksum=hashlib.sha256()
    with (snapshot/index[h]).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):checksum.update(chunk)
    if checksum.hexdigest()!=SHARD_SHA:raise ValueError('released HF shard hash mismatch')
    die_width=(129280+95)//96;sm_width=(die_width+31)//32
    first=die*die_width+sm*sm_width;die_end=min((die+1)*die_width,129280)
    rows=min(sm_width,die_end-first)
    if rows<=0:raise ValueError('idle SM has no Markov rows')
    w,k,wr=read_rows(snapshot,index,h,first,rows)
    x,kx,xr=read_rows(snapshot,index,e,token,1)
    if wr['shape']!=[129280,256] or xr['shape']!=[129280,256] or k!=256 or kx!=k:
        raise ValueError('released fullshape Markov129280x256 required')
    wb=struct.unpack('<'+'H'*(rows*k),w);xb=struct.unpack('<'+'H'*k,x)
    # Native group-slot issue order: eight row slots,8 terms,64 BF16 lanes.
    lines=[]
    for wave in range(0,rows,8):
        for t in range(8):
            for row in range(wave,min(rows,wave+8)):
                word=sum(wb[row*k+8*j+t]<<(16*j) for j in range(32))
                lines.append(word)
    # NC8 full25216-bit words, only real column0 active. Every inactive operand
    # is explicit padded storage, never a substitute for the active released row.
    xs=[sum(xb[8*j+t]<<(2128+16*j) for j in range(32)) for t in range(8)]
    record=[rows,8,1,0,len(lines),1,1,8,1,0]
    # Call the actual released reference; importing its module does not load a model.
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import numpy as np
    import hdc_golden as G
    import hdc_golden_v41 as V
    V.set_arith('chunk8')
    ww=G.from_bits(np.asarray(wb,dtype=np.uint32)<<16).reshape(rows,k)
    xx=G.from_bits(np.asarray(xb,dtype=np.uint32)<<16)
    golden=G.bits(V.csum(G.mul(ww,xx[None,:])))
    if not np.isfinite(G.from_bits(golden)).all():raise ValueError('nonfinite released matvec')
    combined=None;dlog=None;dlog_receipt=None
    if dlog_fixture is not None:
        fixture=Path(dlog_fixture);raw_fixture=fixture.read_bytes()
        if sha(raw_fixture)!='9b3502ec63d2931d20fb0f8d1dd30f35299898a0b8c82bb9baad15ff5e9f4a49':
            raise ValueError('source-pinned component head reference required')
        z=np.load(fixture);dlog=z['logits'][first:first+rows].astype(np.float32)
        if not np.isfinite(dlog).all() or not np.any(dlog!=0):raise ValueError('real nonzero stored logits required')
        combined=G.bits(G.add(dlog,G.from_bits(golden)))
        dlog_receipt=dict(path=str(fixture),sha256=sha(raw_fixture),
            scope='golden/backbone fixture validated by native head component; not native DHEAD production capture',
            logits_slice_sha256=sha(dlog.tobytes()))
    out.mkdir(parents=True,exist_ok=False)
    for name,vals,bits in [('seq.hex',record,32),('lines.hex',lines,1088),('x.hex',xs,25216)]:
        (out/name).write_text(''.join(f'{v:0{(bits+3)//4}x}\n' for v in vals))
    (out/'gold.hex').write_text(''.join(f'{int(v):08x}\n' for v in golden))
    if combined is not None:
        (out/'dlog.hex').write_text(''.join(f'{int(v):08x}\n' for v in G.bits(dlog)))
        (out/'combined.hex').write_text(''.join(f'{int(v):08x}\n' for v in combined))
        winner=int(np.argmax(G.from_bits(combined)))+first
        (out/'winner.hex').write_text(f'{winner:08x}\n')
    r=dict(schema='opentallas.native_sm.payload.v1',nc=8,active_columns=1,
        provenance=dict(scope='released full-shape Markov matvec; no stored-DLOG or argmax',
            released_revision=REVISION,index_sha256=sha(index_raw),weights=wr,activation=xr),
        released_shard_sha256=SHARD_SHA,
        golden_source_sha256={str(Path(m.__file__)):sha(Path(m.__file__).read_bytes()) for m in (G,V)},
        compiler_source_sha256=sha(Path(__file__).read_bytes()),
        stored_logit_fixture=dlog_receipt,
        arithmetic_contract='chunk8',shape=dict(rows=rows,K=k,die=die,sm=sm,global_first_row=first),
        artifacts={p.name:dict(path=p.name,sha256=sha(p.read_bytes())) for p in out.glob('*.hex')},
        numerical_qualified=False,whole_token_qualified=False,hardware_installed=False)
    (out/'payload.json').write_text(json.dumps(r,indent=2)+'\n')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',required=True)
    p.add_argument('--out',required=True);p.add_argument('--token',type=int,default=21946)
    p.add_argument('--die',type=int,default=0);p.add_argument('--sm',type=int,default=0)
    p.add_argument('--dlog-fixture')
    a=p.parse_args();print(json.dumps(generate(a.snapshot,a.out,a.token,a.die,a.sm,a.dlog_fixture)))

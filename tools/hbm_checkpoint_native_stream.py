#!/usr/bin/env python3
"""Stream released source rows into versioned full-native packed136 HBM images.

No model tensor is loaded whole. A bounded eight-item GS issue wave is decoded,
packed and independently compared to the established SM packer. The output is a
source-backed installation INPUT, not a claim of actual command ACK/readback.
"""
import argparse, hashlib, itertools, json, math, shutil
from pathlib import Path
import numpy as np
from dsrom_checkpoint import Checkpoint, DEFAULT_CHECKPOINT
from hbm_checkpoint_native_plan import descriptor, block_bytes, ROOT
from hbm_svc_packed136_image import mapped_sector, sector_pc
from hgi_e2e import sm_lines as SL
import hdc_golden_v41 as V


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

class Source:
    def __init__(self,checkpoint,matrix,expert,rank):
        self.ck=checkpoint; self.m=matrix; self.rank=rank; self.sources={}; self.max_row_bytes=0
        names=matrix['source_tensors']
        self.names=[names[expert]] if matrix['experts']>1 else names
    def row(self,logical):
        row=logical
        for name in self.names:
            meta=self.ck.descriptor(name)[2]
            if row<meta['shape'][0]:break
            row-=meta['shape'][0]
        else:raise ValueError('composite source row bounds')
        dtype=meta['dtype'];cols=meta['shape'][1]
        width={'BF16':2,'F32':4,'F8_E4M3':1,'I8':1}[dtype]
        k=self.m['source_k'];c0=(self.rank%8)*512 if self.m['source_function']=='wo_a_part' else 0
        if c0+k>cols*(2 if dtype=='I8' else 1):raise ValueError('source K slice bounds')
        off=c0//2 if dtype=='I8' else c0*width
        length=k//2 if dtype=='I8' else k*width
        raw=self.ck.raw(name,row*cols*width+off,length)
        scale=None;scname=name[:-7]+'.scale'
        if dtype in ('F8_E4M3','I8'):
            smeta=self.ck.descriptor(scname)[2];sr=row if dtype=='I8' else row//32
            scale=self.ck.raw(scname,sr*smeta['shape'][1]+c0//32,math.ceil(k/32))
            self.sources[scname]=smeta
        self.sources[name]=meta;self.max_row_bytes=max(self.max_row_bytes,len(raw)+len(scale or b''))
        fmt=self.m['format']
        if fmt=='fp8' and dtype!='F8_E4M3' or fmt=='fp4' and dtype!='I8':raise ValueError('released format mismatch')
        if fmt=='bf16':
            if dtype=='BF16':bits=np.frombuffer(raw,dtype='<u2').copy()
            elif dtype=='F32':bits=(V.to_bf16(np.frombuffer(raw,dtype='<f4')).view(np.uint32)>>16).astype('<u2')
            elif dtype=='F8_E4M3':
                codes=np.frombuffer(raw,dtype=np.uint8);e=np.frombuffer(scale,dtype=np.uint8).astype(np.int64)-127
                dense=(V.E4M3[codes]*np.exp2(np.repeat(e,32)[:k])).astype(np.float32)
                bits=(V.to_bf16(dense).view(np.uint32)>>16).astype('<u2')
            else:raise ValueError('unsupported BF16 source decode')
            return bits.tobytes(),None
        return raw,scale


def row_lines(raw,sc,fmt,k):
    la={'bf16':64,'fp8':4,'fp4':8}[fmt];gcount=math.ceil(k/{'bf16':512,'fp8':1024,'fp4':2048}[fmt])
    out=[]
    for g in range(gcount):
        for t in range(8):
            line=bytearray(136)
            for j in range(la):
                b=(g*la+j)*8+t
                if fmt=='bf16':
                    if b<k:line[2*j:2*j+2]=raw[2*b:2*b+2]
                elif b*32<k:
                    n=16 if fmt=='fp4' else 32
                    line[n*j:n*j+n]=raw[n*b:n*b+n];line[128+j]=sc[b]
            out.append(bytes(line))
    # Independent canonical packer, with exactly one selected source row alive.
    if fmt=='bf16':w=(np.frombuffer(raw,dtype='<u2').astype(np.uint32)<<16).view(np.float32)[None,:];fid=0
    else:
        code=np.frombuffer(raw,dtype=np.uint8)
        q=V.E4M3[code] if fmt=='fp8' else V.E2M1[np.stack((code&15,code>>4),axis=1).reshape(-1)]
        e=np.frombuffer(sc,dtype=np.uint8).astype(np.int64)-127
        w=V.Q8(q[None,:],e[None,:]);fid=1 if fmt=='fp8' else 2
    expected=SL.pack(fid,w).reshape(-1,136)
    if out!=[bytes(x) for x in expected]:raise AssertionError('raw source/canonical SM pack mismatch')
    return out


def records(source,d):
    k=d['source_k'];fmt=d['source_format'];gcount=math.ceil(k/{'bf16':512,'fp8':1024,'fp4':2048}[fmt])
    # Canonical GS order: row/group items in waves of8; t then slot.
    items=((r,g) for r in range(d['source_row_count']) for g in range(gcount))
    while True:
        wave=list(itertools.islice(items,8))
        if not wave:return
        cache={}
        for r,g in wave:
            if r not in cache:
                raw,sc=source.row(d['source_row_first']+32*r)
                cache[r]=row_lines(raw,sc,fmt,k)
        for t in range(8):
            for r,g in wave:yield cache[r][g*8+t]


def physical(j,d):
    t=j//4;row=d['region_row_base']+(t>>10)
    if not 16640<=row<18688:raise ValueError('full-native reserved row bounds')
    s=mapped_sector(d['pcs'][j%4],((t>>7)&7)*4+(t&3),row,(t>>2)&31)
    if (s+1)*32>22500000000 or sector_pc(s)!=d['pcs'][j%4]:raise ValueError('physical capacity/map')
    return s


def export(snapshot,out,rank,sm,index,expert):
    residency_path=ROOT/'results/arch/hbm_die_v15/checkpoint_residency/receipt.json'
    book_path=ROOT/'results/arch/hbm_die_v15/full_native_checkpoint_plan/book.json'
    r=json.loads(residency_path.read_text());book=json.loads(book_path.read_text());m=r['matrices'][index]
    if book['source_sha256'][str(residency_path.relative_to(ROOT))]!=digest(residency_path):raise ValueError('residency hash drift')
    ck=Checkpoint(snapshot)
    if digest(ck.root/'model.safetensors.index.json')!=r['checkpoint_index_sha256']:raise ValueError('released checkpoint identity')
    d=descriptor(r,rank,sm,index,expert)
    if d['packed_sector_offset']+d['sectors']>book['per_SM_capacity_bytes']//32:raise ValueError('descriptor capacity')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    # Text images require approximately2.4x binary; preserve1GiB headroom.
    if shutil.disk_usage(out).free<d['sectors']*80+(1<<30):out.rmdir();raise ValueError('output headroom')
    source=Source(ck,m,expert,rank);buf=bytearray();count=0;sector_count=0;logical=hashlib.sha256();image=hashlib.sha256()
    with (out/'records.hex').open('x') as rec,(out/'physical.hex').open('x') as phy:
        def emit(data):
            nonlocal sector_count
            j=d['packed_sector_offset']+sector_count;s=physical(j,d)
            text=f'@{s:08x}\n{int.from_bytes(data,"little"):064x}\n';phy.write(text);image.update(text.encode());sector_count+=1
        for line in records(source,d):
            rec.write(f'{int.from_bytes(line,"little"):0272x}\n');logical.update(line);buf.extend(line);count+=1
            while len(buf)>=32:emit(bytes(buf[:32]));del buf[:32]
        while sector_count<d['sectors']:
            emit(bytes(buf)+bytes(32-len(buf)));buf.clear()
    if count!=d['payload_records'] or sector_count!=d['sectors']:raise AssertionError('source/packed extent count')
    receipt=dict(schema='opentallas.hbm.full-native-streamed-image.v1',status='SOURCE_PAYLOAD_EXPORTED_ACTUAL_COMMAND_INSTALL_REQUIRED',
        descriptor=d,checkpoint_revision=r['checkpoint_revision'],checkpoint_index_sha256=r['checkpoint_index_sha256'],
        source_tensor_headers=source.sources,actual_source_payload_bytes_read=ck.read_bytes,
        source_row_decode='exact checkpoint codes/scales; wo_a and BF16 sources follow canonical BF16 conversion; no surrogate weights',
        layout='versioned modulo32 SM rows; canonical GS wave8,t,slot record order; immutable136B record',
        records=count,sectors=sector_count,logical_payload_sha256=logical.hexdigest(),physical_hex_sha256=image.hexdigest(),
        records_file_sha256=digest(out/'records.hex'),book_sha256=digest(book_path),residency_sha256=digest(residency_path),
        independent_canonical_SM_packer_rows_checked=d['source_row_count'],
        source_buffer_bound_bytes=8*(source.max_row_bytes+m['packed_bytes_per_row']),
        source_sha256={p:digest(ROOT/p) for p in ['tools/hbm_checkpoint_native_stream.py','tools/hbm_checkpoint_native_plan.py','tools/dsrom_checkpoint.py','tools/hgi_e2e/sm_lines.py','tools/hdc_golden_v41.py']},
        actual_command_ACK_verified=False,actual_command_readback_verified=False,native_programme_qualified=False,performance_qualified=False,physical_qualified=False)
    ck.close();(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(records=count,sectors=sector_count,packed_sector_offset=d['packed_sector_offset'],out=str(out))))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--enable-full-native',action='store_true');p.add_argument('--snapshot',default=str(DEFAULT_CHECKPOINT));p.add_argument('--out',required=True);p.add_argument('--rank',type=int,required=True);p.add_argument('--sm',type=int,required=True);p.add_argument('--matrix',type=int,required=True);p.add_argument('--expert',type=int,default=0);a=p.parse_args()
    if not a.enable_full_native:p.error('explicit versioned full-native mode required')
    export(a.snapshot,a.out,a.rank,a.sm,a.matrix,a.expert)

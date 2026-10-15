#!/usr/bin/env python3
"""Replay captured native SVC scores/PV through real SU SE/SO, and extract actual SU VM output.

prepare --capture C.npz --snapshot snap_Lxx.pkl --out W [--stage se|so]
Then run tools/s81_suhc/su_gate.py run --shape full --fp rtl --hier --out W.
collect --out W --run NAME

This is a staged component bridge. It establishes data provenance, not continuous
native execution or physical cycle timing. Snapshot supplies declared constants
only (scale, sink, RoPE coefficients). Scores and PV MUST be actual SVC captures.
SE-only extraction does not run SO. SO replay re-executes SE to establish the
actual denominator before consuming captured native PV. Golden values are used
only to check actual output. P-file conversion is explicitly a simulation bridge;
the corresponding on-chip BF16 converter still has to be bound in the chip.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
import su_gate as S

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(a):
    c=np.load(a.capture,allow_pickle=False)
    scores=np.asarray(c['s_raw'],np.float32)
    if scores.ndim!=2 or scores.shape[0]!=16 or not np.isfinite(scores).all():
        raise ValueError('capture must contain finite actual scores [16,T]')
    if a.stage=='so':
        pv=np.asarray(c['pv'],np.float32)
        if pv.shape!=(16,512) or not np.isfinite(pv).all():raise ValueError('missing or invalid native PV')
    else:pv=np.zeros((16,512),np.float32)  # Not executed: SO removed below.
    snap=pickle.loads(Path(a.snapshot).read_bytes())
    at=snap['hc']['attend'];cos,sin=at['cs']
    r=S.Run(S.SHAPES['full'])
    r.softmax(scores,np.float32(at['attn_scale']),np.asarray(at['sink'],np.float32),pv,
              np.asarray(cos,np.float32),np.asarray(sin,np.float32))
    erow,ecount=r.jexp[0];orow,ocount=r.jexp[1]
    if a.stage=='se':
        r.prog.pop();r.jexp.pop(1)
        for i in range(ocount):r.exp.pop(orow+i)
    name='native_service_'+a.stage
    meta=dict(run=name,shape='full',jobs=len(r.prog),exp_rows=len(r.exp))
    r.write(a.out/'runs'/name,meta)
    (a.out/'runs.json').write_text(json.dumps(dict(runs=[meta],shape='full',params=S.SHAPES['full']))+'\n')
    manifest=dict(schema='opentallas.s81_su.service_bridge.v1',run=name,stage=a.stage,T=int(scores.shape[1]),
        e=dict(row=erow,count=ecount),o=dict(row=orow,count=ocount),
        expected_address_order=sorted(r.exp),capture_sha256=digest(a.capture),snapshot_sha256=digest(a.snapshot),
        snapshot_used=['attn_scale','sink','cs'],scores_source='native SVC capture',
        pv_source='native SVC capture' if a.stage=='so' else 'not executed',
        scope='staged component replay, not native full-token or physical timing qualification')
    (a.out/'bridge.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(name,'T',manifest['T'],'jobs',len(r.prog))

def collect(a):
    m=json.loads((a.out/'bridge.json').read_text());d=a.out/'runs'/m['run']
    actual=[int(x,16) for x in (d/'got.mem').read_text().splitlines()]
    addresses=m['expected_address_order']
    if len(actual)!=len(addresses):raise ValueError('incomplete actual output dump')
    rows=dict(zip(addresses,actual))
    def words(row,n,bits):
        return np.asarray([(rows[row+i]>>(bits*j))&((1<<bits)-1)
                    for i in range(n) for j in range(512//bits)],dtype=np.uint32)
    T=m['T'];nv=(T+15)//16
    ew=words(m['e']['row'],m['e']['count'],32).reshape(nv,16,16)
    e=ew.transpose(1,0,2).reshape(16,nv*16)[:,:T].copy()
    result=dict(e_bits=e)
    # RNE conversion is a declared simulation-boundary bridge. It must not be
    # mistaken for proof that a native converter exists in the integrated die.
    p=((e.astype(np.uint64)+0x7fff+((e>>16)&1))>>16).astype(np.uint16)
    result['p_bits']=p
    packed=[]
    for w in range((T+1)//2):
        v=0
        for jj in range(2):
            for h in range(16):
                if 2*w+jj<T:v|=int(p[h,2*w+jj])<<(16*(jj*16+h))
        packed.append(f'{v:0128x}\n')
    (d/'native_p.hex').write_text(''.join(packed))
    if m['stage']=='so':
        ow=words(m['o']['row'],m['o']['count'],16).reshape(32,16,16)
        result['o_bits']=ow.transpose(1,0,2).reshape(16,512).astype(np.uint16)
    np.savez(d/'native_output.npz',**result)
    print('ACTUAL SU output',d/'native_output.npz','P bridge',d/'native_p.hex')

def main():
    p=argparse.ArgumentParser(description=__doc__);sp=p.add_subparsers(dest='cmd',required=True)
    q=sp.add_parser('prepare');q.add_argument('--capture',type=Path,required=True);q.add_argument('--snapshot',type=Path,required=True)
    q.add_argument('--stage',choices=['se','so'],default='so');q.add_argument('--out',type=Path,required=True)
    q=sp.add_parser('collect');q.add_argument('--out',type=Path,required=True)
    a=p.parse_args();dict(prepare=prepare,collect=collect)[a.cmd](a)
if __name__=='__main__':main()

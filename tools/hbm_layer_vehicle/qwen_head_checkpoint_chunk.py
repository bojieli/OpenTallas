#!/usr/bin/env python3
"""Prepare one actual checkpoint HEAD row chunk without evaluating the full projection.

extract needs lazy safetensors/numpy; quantize needs the deployed Torch quantizer;
compile uses existing arithmetic/packed136 component compiler. Run compute on ot-run.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
import qwen_r25_golden as R

def extract(snapshot,out,rank=0,first_row=0,rows=512):
    ck=R.Checkpoint(snapshot);rank_rows=ck.cfg['vocab_size']//8
    if ck.cfg['vocab_size']%8 or not 0<=rank<8 or first_row<0 or not 1<=rows<=512 or first_row+rows>rank_rows:
        raise ValueError('chunk must lie inside one actual TP8 rank and contain at most512rows')
    lo=rank*rank_rows+first_row
    out.mkdir(parents=True,exist_ok=True)
    np.savez(out/'source.npz',W=ck.get('lm_head.weight',rows=(lo,lo+rows)),
        embedding=ck.get('model.embed_tokens.weight',rows=(9707,9708)),norm=ck.get('model.norm.weight'))
    (out/'source.json').write_text(json.dumps(dict(snapshot=str(snapshot),checkpoint_rows=[lo,lo+rows],rank=rank,
        rank_full_rows=rank_rows,K=ck.cfg['hidden_size'],eps=ck.cfg['rms_norm_eps'],
        activation='qwen_d4g_proof.golden(head): synthetic_x(model,1), row9707 embedding +seed[8191,1,1] then final RMSNorm',
        scope='actual checkpoint chunk only, no fullrank projection'),indent=2)+'\n')

def quantize(out):
    z=np.load(out/'source.npz')
    image=R.Image(None,out/'cache')
    W,_=image._quant(z['W']);E,es=image._quant(z['embedding'])
    np.savez(out/'quantized.npz',W=W,embedding=E,embedding_scale=es,norm=z['norm'])

def compile_actual(out):
    from hgi_sim import lib
    from qwen_head_chunks import compile_chunks
    z=np.load(out/'quantized.npz');meta=json.loads((out/'source.json').read_text())
    W,E,es=z['W'],z['embedding'],z['embedding_scale']
    # Embedding quantization is per row; read/quantize only the row used by canonical synthetic_x.
    x=R.G.add(R.G.mul(E[0].astype(np.float32),es[0]),
        (np.random.default_rng([8191,1,1]).standard_normal(meta['K'])*0.5).astype(np.float32))
    h=R.rmsnorm(x,z['norm'],meta['eps']);O=lib.sm_int8(W,h)
    kv=out/'kv';kv.mkdir(exist_ok=True);np.savez(kv/'sm_mv.npz',W=W,A=h,O=O)
    (kv/'sm_mv.json').write_text(json.dumps(dict(records=[dict(rank=meta['rank'],L=0,tag='head',
        arrays={k:dict(key=k) for k in ('W','A','O')})])))
    result=compile_chunks(kv,0,meta['rank'],out/'compiled',partitions=1,chunk_rows=len(W),rows=len(W),columns=meta['K'])
    result['checkpoint_source']=meta
    result['scope']='one actual checkpoint row chunk, not fullrank projection or source-bound STREAM/physical qualification'
    (out/'actual_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('ACTUAL_HEAD_CHUNK_PASS',W.shape,'descs',result['chunks'][0]['component']['budget']['descriptors'],
        'store',result['chunks'][0]['component']['budget']['store_top'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('extract','quantize','compile'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--snapshot',type=Path)
    p.add_argument('--rank',type=int,default=0);p.add_argument('--first-row',type=int,default=0);p.add_argument('--rows',type=int,default=512)
    a=p.parse_args()
    if a.action=='extract':
        if not a.snapshot:p.error('extract requires --snapshot')
        extract(a.snapshot,a.out,a.rank,a.first_row,a.rows)
    elif a.action=='quantize':quantize(a.out)
    else:compile_actual(a.out)
